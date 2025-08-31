/* eslint-env browser */
/* global io */

const DEBUG = false;

// --- Constants and Global Variables ---
let numRequestsInProgress = 0;
let querySendInProgress = false;
let chatFetchInProgress = false;
let toolUseFetchInProgress = false;
let messageInput = null; // Declare messageInput globally
const marked = new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true });

// Socket.IO connection
let socket = null;
let isConnected = false;

// Track total cost and tokens
const totalTokens = 0;
const totalCost = 0;
const SESSION_HISTORY_KEY = 'sessionHistory';

// Track tool use reporting
let previousToolUseContent = '';
let lastReportedToolUseTimestamp = null;

const MODEL_DEFAULT_CATEGORY = 'medium';

function sanitizeModelCategory(modelCategory) {
  if (!['easy', 'medium', 'hard'].includes(modelCategory)) {
    return MODEL_DEFAULT_CATEGORY;
  }
  return modelCategory;
}

// --- WebSocket Connection Management ---
function initializeWebSocket() {
  if (socket) {
    socket.disconnect();
  }

  socket = io(); // Use current host automatically

  socket.on('connect', () => {
    isConnected = true;
    if (DEBUG) console.log('Connected to WebSocket server');
    updateConnectionStatus();
  });

  socket.on('disconnect', () => {
    isConnected = false;
    if (DEBUG) console.log('Disconnected from WebSocket server');
    updateConnectionStatus();
  });

  socket.on('connection_confirmed', (data) => {
    if (DEBUG) console.log('Connection confirmed:', data);
    showAlert('Connected to Agent Coding Assistant', 'success');
    
    // Request session history after connection is confirmed
    socket.emit('load_session_history', { session_id: getSessionIdFromUrlOrStore() });
  });

  // --- Streaming state & helpers ---
  let currentStreamingMessage = null;
  let streamingContent = '';

  function startStreamingBotMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const timeObj = getCurrentTime();
    const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
    const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;

    const messageHTML = `
      <div class="message-wrapper streaming-message">
          <div class="avatar-and-message">
              <div class="chat-avatar bot-avatar">AI</div>
              <div class="message bot-message">
                  <p class="streaming-content"></p>
                  <small class="clearfix">
                      <span class="metadata-info"></span>
                      <span class="time-info" title="${fullTime}">${shortTime}</span>
                  </small>
              </div>
          </div>
      </div>
    `;

    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    currentStreamingMessage = chatMessages.querySelector('.streaming-message:last-child');
    streamingContent = '';
  }

  function appendToStreamingMessage(chunk) {
    if (!currentStreamingMessage) return;
    streamingContent += chunk;
    const contentElement = currentStreamingMessage.querySelector('.streaming-content');
    if (contentElement) {
      contentElement.innerHTML = convertToSafeHtml(streamingContent);
    }
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function finalizeStreamingMessage(finalAnswer, modelName = null, tokenInfo = null) {
    if (!currentStreamingMessage) return;
    const contentElement = currentStreamingMessage.querySelector('.streaming-content');
    if (contentElement) {
      contentElement.innerHTML = convertToSafeHtml(finalAnswer);
    }

    // Populate metadata (model + tokens) if available
    try {
      const metadataSpan = currentStreamingMessage.querySelector('.metadata-info');
      const normalized = tokenInfo ? parseUsageMetadata(tokenInfo) : null;
      const model = modelName || (normalized && normalized.model) || localStorage.getItem('lastResponseModel') || '';

      if (normalized) {
        localStorage.setItem('lastResponseTokens', JSON.stringify(normalized));
        if (normalized.model) localStorage.setItem('lastResponseModel', normalized.model);
      }

      if (metadataSpan) {
        const modelHtml = model ? `<span class="model-info">${model}</span>` : '';
        let tokenInfoHtml = '';
        if (normalized && (normalized.prompt_tokens != null || normalized.completion_tokens != null)) {
          let tokenText = `(Tokens: ${normalized.prompt_tokens || 0} + ${normalized.completion_tokens || 0}`;
          const costStats = normalized.cost_statistics || {};
          const costVal = costStats.total_cost_llm_api_usd || costStats.total_cost || 0;
          if (costVal > 0) {
            tokenText += ` ($${Number(costVal).toFixed(3)})`;
          }
          tokenText += ')';
          tokenInfoHtml = `<span class="token-info">${tokenText}</span>`;
        }
        metadataSpan.innerHTML = `${modelHtml} ${tokenInfoHtml}`.trim();
      }
    } catch (e) {
      // Non-fatal
      if (DEBUG) console.warn('Failed to finalize metadata for streaming message', e);
    }

    currentStreamingMessage.classList.remove('streaming-message');
    currentStreamingMessage = null;
    streamingContent = '';
  }

  socket.on('question_start', (data) => {
    if (DEBUG) console.log('Question started:', data);
    // Clear chat messages for new response
    registerRequestInProgress();
  });

  socket.on('tool_start', (data) => {
    if (DEBUG) console.log('Tool started:', data);
    // Add tool use entry with normalized wording
    const q = (typeof data.query === 'string' && data.query) ? data.query : '';
    const text = q ? `Query is '${q}'` : (data.description || 'started');
    addToolUseEntry(data.tool, text, 'started');
  });

  socket.on('tool_progress', (data) => {
    if (DEBUG) console.log('Tool progress:', data);
    // Add tool progress entry to Tool Use History
    const progressMessage = data.message || data.status || 'in progress';
    const progressText = data.progress != null ? `${progressMessage} (${data.progress}%)` : progressMessage;
    addToolUseEntry(data.tool || 'tool', progressText, 'progress');
  });

  socket.on('tool_complete', (data) => {
    if (DEBUG) console.log('Tool completed:', data);
    // Prefer result_preview; format as requested
    const hasPreview = typeof data.result_preview === 'string' && data.result_preview.length > 0;
    const text = hasPreview ? `Completed - Result: ${data.result_preview}` : 'Completed';
    addToolUseEntry(data.tool, text, 'completed');
  });

  socket.on('tool_error', (data) => {
    if (DEBUG) console.log('Tool error:', data);
    // Show error in tool use
    addToolUseEntry(data.tool, `Error: ${data.error}`, 'error');
  });

  socket.on('answer_chunk', (data) => {
    if (DEBUG) console.log('Answer chunk received');
    // If this is the first chunk, render the user message (if pending) and start streaming container
    if (!currentStreamingMessage) {
      const lastUserMessage = messageInput && messageInput.dataset ? (messageInput.dataset.lastQuestion || '') : '';
      if (lastUserMessage) {
        renderUserMessage(lastUserMessage);
        delete messageInput.dataset.lastQuestion;
      }
      startStreamingBotMessage();
    }
    // Append chunk
    appendToStreamingMessage(data.chunk || '');
  });

  socket.on('grounding_update', (data) => {
    if (DEBUG) console.log('Grounding update:', data);
    // Handle grounding information updates
  });

  socket.on('answer_complete', (data) => {
    if (DEBUG) console.log('Answer complete:', data);

    // If we streamed, finalize the streaming message; otherwise fall back to full render
    if (currentStreamingMessage) {
      finalizeStreamingMessage(data.answer, null, data.usage_metadata || null);
    } else {
      const lastUserMessage = messageInput && messageInput.dataset ? (messageInput.dataset.lastQuestion || '') : '';
      if (lastUserMessage) {
        renderUserMessage(lastUserMessage);
        delete messageInput.dataset.lastQuestion;
      }
      // Normalize metadata and persist for rendering
      const normalized = data.usage_metadata ? parseUsageMetadata(data.usage_metadata) : null;
      if (normalized) {
        try {
          localStorage.setItem('lastResponseTokens', JSON.stringify(normalized));
          if (normalized.model) localStorage.setItem('lastResponseModel', normalized.model);
        } catch (e) {
          if (DEBUG) console.warn('Failed saving last response tokens/model', e);
        }
      }
      renderBotMessage(data.answer, null, normalized ? normalized.model : null, normalized || null);
    }
    
    // Update cost tracking
    if (data.usage_metadata) {
      updateCostFromUsageMetadata(data.usage_metadata);
    }
    
    unregisterRequestInProgress();
    querySendInProgress = false;
    
    // Clear input and reset textarea height
    messageInput.value = '';
    autoResizeTextarea(messageInput);
    
    // Focus back on the textarea
    messageInput.focus();
  });

  socket.on('session_history_loaded', (data) => {
    if (DEBUG) console.log('Session history loaded:', data);
    displaySessionHistory(data.history || []);
  });

  socket.on('error', (data) => {
    if (DEBUG) console.log('WebSocket error:', data);
    showAlert(`Error: ${data.message}`, 'error');
    unregisterRequestInProgress();
    querySendInProgress = false;
  });

  socket.on('question_cancelled', (data) => {
    if (DEBUG) console.log('Question cancelled:', data);
    showAlert('Question processing cancelled', 'info');
    unregisterRequestInProgress();
    querySendInProgress = false;
  });
}

function updateConnectionStatus() {
  // Update UI to reflect connection status
  if (isConnected) {
    document.body.classList.add('connected');
    document.body.classList.remove('disconnected');
  } else {
    document.body.classList.add('disconnected');
    document.body.classList.remove('connected');
  }
}

function displaySessionHistory(history) {
  if (DEBUG) console.log('Displaying session history:', history);
  
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) {
    console.warn('Chat messages container not found');
    return;
  }
  
  // Clear existing messages
  chatMessages.innerHTML = '';
  // Reset per-session cost/token totals before re-accumulating from history
  resetSessionCostData();
  // Clear tool history as we're reloading a session
  const toolUseHistory = document.getElementById('tool-use-history');
  if (toolUseHistory) {
    toolUseHistory.innerHTML = '';
    const emptyMessage = document.getElementById('tool-history-empty');
    if (emptyMessage) emptyMessage.style.display = 'block';
  }
  
  if (!history || history.length === 0) {
    if (DEBUG) console.log('No session history to display, showing welcome message');
    // Show welcome message if no history
    renderBotMessage('Hi! I\'m your Agent Coding Assistant.\n\nI can help you with:\n- Campaign setup and optimization\n- Bidding strategies and performance analysis\n- Google Ads best practices and recommendations\n- Troubleshooting campaign issues\n\nWhat are we gonna build today?');
    return;
  }
  
  // Collect all tools from all conversations for global sorting by newest first
  const allTools = [];
  history.forEach((entry, index) => {
    if (entry.tools && Array.isArray(entry.tools) && entry.tools.length > 0) {
      entry.tools.forEach((tool) => {
        const toolName = tool.name || 'tool';
        let text = '';
        if (tool.status === 'error' && tool.error) {
          const q = tool.input_summary ? `Query is '${tool.input_summary}'\n` : '';
          text = `${q}Error: ${tool.error}`.trim();
        } else if (tool.status === 'completed') {
          text = tool.result_preview ? `Completed - Result: ${tool.result_preview}` : 'Completed';
        } else {
          text = tool.input_summary ? `Query is '${tool.input_summary}'` : 'started';
        }
        // Prefer ended_at for completed/error, otherwise started_at
        const ts = tool.ended_at || tool.started_at || null;
        allTools.push({
          toolName,
          text,
          status: tool.status || 'started',
          timestamp: ts
        });
      });
    }
  });

  // Sort all tools globally by newest first (descending timestamp order)
  allTools.sort((a, b) => {
    const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return tb - ta; // Newest first
  });

  // Display each conversation pair
  history.forEach((entry, index) => {
    // Display user question
    renderUserMessage(entry.question);

    // Display bot answer with token/model info if available
    let normalized = null;
    if (entry.usage_metadata) {
      normalized = parseUsageMetadata(entry.usage_metadata);
    }
    renderBotMessage(entry.answer, null, normalized ? normalized.model : null, normalized || null);

    // Update cost information if available
    if (entry.usage_metadata) {
      updateCostFromUsageMetadata(entry.usage_metadata);
    }
  });

  // Add all tools to history in globally sorted order (newest first)
  if (allTools.length > 0) {
    // Ensure section visible
    const toolUseSection = document.getElementById('toolUseSection');
    if (toolUseSection) toolUseSection.style.display = 'block';

    // Add tools in sorted order (newest first)
    allTools.forEach((toolData) => {
      addToolUseEntry(toolData.toolName, toolData.text, toolData.status, toolData.timestamp, true);
    });
  }
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  if (DEBUG) console.log(`Displayed ${history.length} conversation entries`);
}

// --- Tool Use History Management ---
function addToolUseEntry(toolName, input, status = 'started', timestamp = null, isHistoryLoad = false) {
  const toolUseHistory = document.getElementById('tool-use-history');
  const emptyMessage = document.getElementById('tool-history-empty');
  
  if (!toolUseHistory) return;
  
  // Show the tool use section
  const toolUseSection = document.getElementById('toolUseSection');
  if (toolUseSection) {
    toolUseSection.style.display = 'block';
  }
  
  // Hide empty message
  if (emptyMessage) {
    emptyMessage.style.display = 'none';
  }
  
  // Create timestamp
  const now = timestamp ? new Date(timestamp) : new Date();
  const formattedTimestamp = now.toLocaleTimeString();
  
  // Create status badge based on status
  let statusBadge = '';
  if (status === 'progress') {
    statusBadge = '<span class="tool-status-badge progress">●</span>';
  } else if (status === 'completed') {
    statusBadge = '<span class="tool-status-badge completed">✓</span>';
  } else if (status === 'error') {
    statusBadge = '<span class="tool-status-badge error">✗</span>';
  }

  // Create tool entry HTML
  const toolEntry = document.createElement('div');
  toolEntry.className = 'tool-entry';
  toolEntry.innerHTML = `
    <div class="tool-timestamp">${formattedTimestamp}</div>
    <div class="tool-bubble">
      <div class="tool-name">${toolName.toUpperCase()}${statusBadge}</div>
      <div class="tool-input">${input}</div>
    </div>
  `.trim();
  
  // Always insert in chronological order (newest first)
  // For live updates, prepend to maintain newest-first order
  // For history loading, append since tools are already sorted globally by newest first
  if (!isHistoryLoad) {
    // Live update: prepend to top (newest)
    toolUseHistory.insertBefore(toolEntry, toolUseHistory.firstChild);
  } else {
    // History loading: append since tools are pre-sorted by newest first
    toolUseHistory.appendChild(toolEntry);
  }
  
  // Limit to last 20 entries for live updates only
  if (!isHistoryLoad) {
    const entries = toolUseHistory.querySelectorAll('.tool-entry');
    if (entries.length > 20) {
      entries[entries.length - 1].remove();
    }
  }
}

// --- Sidebar collapse functions ---
function getSidebarCollapseState() {
  // Default to collapsed (true) if not set
  const storedValue = localStorage.getItem('sidebarCollapsed');
  return storedValue === null ? true : storedValue === 'true';
}

function setSidebarCollapseState(isCollapsed) {
  localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
}

function toggleSidebar(forceOpen = false) {
  const sidebar = document.getElementById('settings-sidebar');
  const chatArea = document.getElementById('chat-area');
  const isCollapsed = sidebar.classList.contains('collapsed');
  
  // If forceOpen is true, we only want to expand (not toggle)
  // Only take action if sidebar is collapsed or we're not forcing open
  if (DEBUG) console.log('toggleSidebar', isCollapsed, forceOpen);
  if (isCollapsed || (!isCollapsed && !forceOpen)) {
    if (isCollapsed || forceOpen) {
      // Expand
      sidebar.classList.remove('collapsed');
      chatArea.classList.remove('col-md-12');
      chatArea.classList.add('col-md-9');
      setSidebarCollapseState(false);
    } else {
      // Collapse
      sidebar.classList.add('collapsed');
      chatArea.classList.remove('col-md-9');
      chatArea.classList.add('col-md-12');
      setSidebarCollapseState(true);
    }
  }
}

function applySidebarCollapseState() {
  const isCollapsed = getSidebarCollapseState();
  const sidebar = document.getElementById('settings-sidebar');
  const chatArea = document.getElementById('chat-area');
  
  // Temporarily disable transitions to prevent animation on page load
  document.body.classList.add('no-transition');
  
  if (isCollapsed) {
    sidebar.classList.add('collapsed');
    chatArea.classList.remove('col-md-9');
    chatArea.classList.add('col-md-12');
  } else {
    sidebar.classList.remove('collapsed');
    chatArea.classList.remove('col-md-12');
    chatArea.classList.add('col-md-9');
  }
  
  // Re-enable transitions after a brief delay
  setTimeout(() => {
    document.body.classList.remove('no-transition');
  }, 50);
}

// --- Toggle dark mode ---
function toggleDarkMode() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  
  // Toggle the state
  const isDarkMode = localStorage.getItem('darkMode') === 'true';
  const newDarkModeState = !isDarkMode;
  
  // Update localStorage
  localStorage.setItem('darkMode', newDarkModeState.toString());
  
  // Update checkbox state
  if (darkModeToggle) {
    darkModeToggle.checked = newDarkModeState;
  }
  
  // Update body class
  if (newDarkModeState) {
    document.body.classList.add('dark-mode');
  } else {
    document.body.classList.remove('dark-mode');
  }
  
  // Update button icon - show the opposite of current state (what will happen on next click)
  updateDarkModeButtonIcon();
}

// Update button icon based on current dark mode state
// Now shows what it will become when clicked (reversed logic)
function updateDarkModeButtonIcon() {
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  if (toggleDarkModeBtn) {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    const iconElement = toggleDarkModeBtn.querySelector('i');
    if (iconElement) {
      // Reversed logic - show sun if in dark mode, moon if in light mode
      if (isDarkMode) {
        iconElement.classList.remove('bi-moon-fill');
        iconElement.classList.add('bi-sun-fill');
      } else {
        iconElement.classList.remove('bi-sun-fill');
        iconElement.classList.add('bi-moon-fill');
      }
    }
  }
}

// --- Alert function ---
function showAlert(message, type = 'error') {
  // Create alert element if it doesn't exist
  let alertElement = document.getElementById('clarity-alert');
  if (!alertElement) {
    alertElement = document.createElement('div');
    alertElement.id = 'clarity-alert';
    alertElement.style.position = 'fixed';
    alertElement.style.top = '80px';
    alertElement.style.right = '30px';
    alertElement.style.padding = '12px 20px';
    alertElement.style.borderRadius = '6px';
    alertElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    alertElement.style.zIndex = '1000';
    alertElement.style.maxWidth = '450px';
    alertElement.style.opacity = '0';
    alertElement.style.visibility = 'hidden';
    alertElement.style.pointerEvents = 'none';
    alertElement.style.transition = 'opacity 0.3s ease, visibility 0.3s ease';
    alertElement.style.fontSize = '16px';
    alertElement.style.display = 'flex';
    alertElement.style.alignItems = 'center';
    alertElement.style.justifyContent = 'space-between';
    document.body.appendChild(alertElement);
  }

  // Set background color based on type
  if (type === 'error') {
    alertElement.style.backgroundColor = 'rgba(220, 53, 69, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #dc3545';
  } else if (type === 'warning') {
    alertElement.style.backgroundColor = 'rgba(255, 193, 7, 0.95)';
    alertElement.style.color = 'black';
    alertElement.style.borderLeft = '5px solid #ffc107';
  } else if (type === 'info') {
    alertElement.style.backgroundColor = 'rgba(66, 165, 245, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #42a5f5';
  } else if (type === 'success') {
    alertElement.style.backgroundColor = 'rgba(25, 135, 84, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #198754';
  } 

  // Create content wrapper with improved close button functionality
  const contentHTML = `
    <div style="flex: 1">${message}</div>
    <button style="background: transparent; border: none; color: inherit; cursor: pointer; font-size: 18px; margin-left: 10px;" onclick="hideAlert();">×</button>
  `;

  // Update alert content and show
  alertElement.innerHTML = contentHTML;
  alertElement.style.opacity = '1';
  alertElement.style.visibility = 'visible';
  alertElement.style.pointerEvents = 'auto';

  // Auto-hide after 5 seconds
  setTimeout(() => {
    hideAlert();
  }, 5000);
}

// Helper function to properly hide the alert
function hideAlert() {
  const alertElement = document.getElementById('clarity-alert');
  if (alertElement) {
    alertElement.style.opacity = '0';
    alertElement.style.visibility = 'hidden';
    alertElement.style.pointerEvents = 'none';
  }
}

// --- Request tracking functions ---
function registerRequestInProgress() {
  numRequestsInProgress++;
  document.body.classList.add('loading');
  // You could add a loading indicator here
}

function unregisterRequestInProgress() {
  numRequestsInProgress--;
  if (numRequestsInProgress <= 0) {
    document.body.classList.remove('loading');
    numRequestsInProgress = 0;
  }
}

// --- Session and Password Management ---
function getSessionIdFromUrlOrStore() {
  // First try to get from URL
  const urlParams = new URLSearchParams(window.location.search);
  let sessionIdParam = urlParams.get('session_id');
    
  if (sessionIdParam) {
    // Check if the session ID contains _new_ and replace it with current date/time
    if (sessionIdParam.includes('_new_')) {
      const now = new Date();
      const formattedDateTime = now.getFullYear() + 
        String(now.getMonth() + 1).padStart(2, '0') + 
        String(now.getDate()).padStart(2, '0') + '_' +
        String(now.getHours()).padStart(2, '0') + 
        String(now.getMinutes()).padStart(2, '0') + 
        String(now.getSeconds()).padStart(2, '0');
      
      // Replace _new_ with the formatted date/time
      const newSessionId = sessionIdParam.replace('_new_', formattedDateTime);
      
      // Update the URL with the new session ID
      const url = new URL(window.location.href);
      url.searchParams.set('session_id', newSessionId);
      window.history.replaceState(null, '', url.toString());
      
      sessionIdParam = newSessionId;
      if (DEBUG) console.log('Replaced _new_ in session ID with current date/time:', newSessionId);
    }
    
    // Store in localStorage for persistence
    addOrUpdateSessionInHistory(sessionIdParam);
    localStorage.setItem('sessionId', sessionIdParam);
    return sessionIdParam;
  }
    
  // Fall back to localStorage
  let storedId = localStorage.getItem('sessionId');
  if (!storedId) {
    // Generate a default ID if none exists
    storedId = 'coding_assistant_' + Date.now();
    addOrUpdateSessionInHistory(storedId);
    localStorage.setItem('sessionId', storedId);
        
    // Update URL with the new session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', storedId);
    window.history.replaceState(null, '', url.toString());
  } else {
    addOrUpdateSessionInHistory(storedId); // Update last_seen_time for existing stored ID
  }
    
  return storedId;
}

function getModelCategoryFromStore() {
  return localStorage.getItem('selectedModel') || MODEL_DEFAULT_CATEGORY;
}

function setModelCategoryInStore(modelCategory) {
  localStorage.setItem('selectedModel', modelCategory);
}

// --- URL parameter handling functions ---
function getUrlParameter(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

// --- Auto-query functionality ---
let autoQueryProcessed = false;

function processAutoQuery() {
  // Only process once per page load
  if (autoQueryProcessed) {
    return;
  }
  
  const queryParam = getUrlParameter('query');
  if (!queryParam) {
    return;
  }
  
  // Mark as processed to prevent multiple executions
  autoQueryProcessed = true;
  
  try {
    // URL decode the query parameter
    const decodedQuery = decodeURIComponent(queryParam);
    
    // Get the input field
    if (!messageInput) {
      console.error('Chat input field not found for auto-query');
      return;
    }
    
    // Only populate if the input field is empty (don't overwrite user input)
    if (messageInput.value.trim() === '') {
      messageInput.value = decodedQuery;
      autoResizeTextarea(messageInput);
      
      // Remove the query parameter from URL to prevent re-execution
      const url = new URL(window.location.href);
      url.searchParams.delete('query');
      window.history.replaceState(null, '', url.toString());
      
      // Show a brief message that auto-query was applied
      showAlert('Auto-submitting query from URL...', 'info');
      
      // Wait a brief moment then auto-submit
      setTimeout(() => {
        sendQuery();
      }, 500);
    }
  } catch (error) {
    console.error('Error processing auto-query:', error);
    showAlert('Error processing query from URL: ' + error.message, 'error');
  }
}

// --- Session ID handling functions ---
function incrementSessionId() {
  const sessionId = document.getElementById('session-id').value.trim();
  
  // Check if the session ID ends with a number
  const match = sessionId.match(/^(.*?)(\d+)$/);
  
  if (match) {
    // Extract the prefix and the numeric part
    const prefix = match[1];
    const numericPart = parseInt(match[2], 10);
    
    // Increment the numeric part
    const newNumericPart = numericPart + 1;
    
    // Create the new session ID
    const newSessionId = prefix + newNumericPart;
    
    // Update the session ID in localStorage
    addOrUpdateSessionInHistory(newSessionId);
    localStorage.setItem('sessionId', newSessionId);
    
    // Update the URL and reload the page
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', newSessionId);
    window.location.href = url.toString();
  } else {
    // Show error message if the session ID doesn't end with a number
    showAlert('Session ID must end with a number to increment it');
  }
}

// --- Convert markdown to HTML ---
function convertToSafeHtml(aiOrToolAnswer) {
  if (aiOrToolAnswer.includes('": "') && aiOrToolAnswer.includes('{') && aiOrToolAnswer.includes('}')) {
    if (DEBUG) console.log('toJson');
    aiOrToolAnswer = '```json\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  } else if (aiOrToolAnswer.includes('<rss')) {
    if (DEBUG) console.log('toXml');
    aiOrToolAnswer = '```xml\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  } else if (aiOrToolAnswer.includes('</style>')) {
    if (DEBUG) console.log('toHtml');
    aiOrToolAnswer = '```html\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  }
    
  let answerHtml = marked.makeHtml(aiOrToolAnswer);
  if (answerHtml.startsWith('<p>') && answerHtml.endsWith('</p>')) {
    answerHtml = answerHtml.substring(3, answerHtml.length - 4);
  }
  answerHtml = answerHtml.replace(/(<a\s+href="[^"]*")/g, '$1 target="_blank" rel="noopener noreferrer"');
  return answerHtml;
}

// --- Chat Message Rendering ---
function renderBotMessage(message, timestamp = null, modelName = null, tokenInfo = null) {
  const chatMessages = document.getElementById('chatMessages');
  const timeObj = timestamp || getCurrentTime();
  // Support both old format (string) and new format (object with short and full properties)
  const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
  const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;
  
  // Try to get model and token info from parameters or localStorage if not provided
  const model = modelName || localStorage.getItem('lastResponseModel') || '';
  const tokens = tokenInfo || safeJsonParse(localStorage.getItem('lastResponseTokens'), {});
  
  if (DEBUG) console.log('converting bot message', message);
  // Convert markdown to HTML using the safe HTML converter
  const messageHtml = convertToSafeHtml(message);
  
  // Create token info HTML if available
  let tokenInfoHtml = '';
  if (tokens && (tokens.prompt_tokens || tokens.completion_tokens)) {
    let tokenText = `(Tokens: ${tokens.prompt_tokens || 0} + ${tokens.completion_tokens || 0}`;
    if (tokens.cost_statistics) {
      const cost = tokens.cost_statistics.total_cost_llm_api_usd || tokens.cost_statistics.total_cost || 0;
      if (cost > 0) {
        tokenText += ` ($${cost.toFixed(3)})`;
      }
    }
    tokenText += ')';
    tokenInfoHtml = `<span class="token-info">${tokenText}</span>`;
  }
  
  // Create model info HTML if available
  const modelInfoHtml = model ? `<span class="model-info">${model}</span>` : '';
  
  const messageHTML = `
    <div class="message-wrapper">
        <div class="avatar-and-message">
            <div class="chat-avatar bot-avatar">AI</div>
            <div class="message bot-message">
                <p>${messageHtml}</p>
                <small class="clearfix">
                    <span class="metadata-info">${modelInfoHtml} ${tokenInfoHtml}</span>
                    <span class="time-info" title="${fullTime}">${shortTime}</span>
                </small>
            </div>
        </div>
    </div>
    `;
  
  chatMessages.insertAdjacentHTML('beforeend', messageHTML);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderUserMessage(message, timestamp = null) {
  const chatMessages = document.getElementById('chatMessages');
  const timeObj = timestamp || getCurrentTime();
  // Support both old format (string) and new format (object with short and full properties)
  const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
  const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;
    
  if (DEBUG) console.log('converting user message', message);
  // Convert markdown to HTML with proper newline handling
  let messageHtml = marked.makeHtml(message);
  if (messageHtml.startsWith('<p>') && messageHtml.endsWith('</p>')) {
    messageHtml = messageHtml.substring(3, messageHtml.length - 4);
  }
    
  const messageHTML = `
    <div class="message-wrapper user-message-wrapper">
        <div class="avatar-and-message">
            <div class="message user-message">
                <p>${messageHtml}</p>
                <small title="${fullTime}">${shortTime}</small>
            </div>
            <div class="chat-avatar user-avatar">U</div>
        </div>
    </div>
    `;
    
  chatMessages.insertAdjacentHTML('beforeend', messageHTML);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getCurrentTime() {
  const now = new Date();
  const formattedTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  // Create a full timestamp for the title attribute
  const fullTimestamp = now.toLocaleString([], {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric'
  });
  return { short: formattedTime, full: fullTimestamp };
}

// --- Session and Cost Management ---
function getSessionTotalCost() {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalCost_${sessionId}`;
  return parseFloat(localStorage.getItem(storageKey) || '0');
}

function getSessionTotalTokens() {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalTokens_${sessionId}`;
  return parseInt(localStorage.getItem(storageKey) || '0');
}

function updateSessionTotalCost(cost) {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalCost_${sessionId}`;
  // Fix floating point precision by multiplying by 1000 first
  const currentCost = Math.round(parseFloat(localStorage.getItem(storageKey) || '0') * 1000) / 1000;
  // Add with precise calculation
  const newCost = (Math.round((currentCost + cost) * 1000)) / 1000;
  localStorage.setItem(storageKey, newCost.toString());
  
  // Update UI
  const totalCostElement = document.getElementById('total-cost');
  if (totalCostElement) {
    totalCostElement.textContent = `$${newCost.toFixed(3)}`;
  }
  
  return newCost;
}

function updateSessionTotalTokens(tokens) {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalTokens_${sessionId}`;
  const currentTokens = parseInt(localStorage.getItem(storageKey) || '0');
  const newTokens = currentTokens + tokens;
  localStorage.setItem(storageKey, newTokens.toString());
  
  // Update UI
  const totalTokensElement = document.getElementById('total-tokens');
  if (totalTokensElement) {
    totalTokensElement.textContent = `${newTokens.toLocaleString()} tokens`;
  }
  
  return newTokens;
}

function loadSessionCostData() {
  const sessionId = getSessionIdFromUrlOrStore();
  const costStorageKey = `sessionTotalCost_${sessionId}`;
  const tokensStorageKey = `sessionTotalTokens_${sessionId}`;
  
  // Fix floating point precision by multiplying by 1000 first
  const cost = Math.round(parseFloat(localStorage.getItem(costStorageKey) || '0') * 1000) / 1000;
  const tokens = parseInt(localStorage.getItem(tokensStorageKey) || '0');
  
  // Update UI
  const totalCostElement = document.getElementById('total-cost');
  const totalTokensElement = document.getElementById('total-tokens');
  
  if (totalCostElement) {
    totalCostElement.textContent = `$${cost.toFixed(3)}`;
  }
  
  if (totalTokensElement) {
    totalTokensElement.textContent = `${tokens.toLocaleString()} tokens`;
  }
  
  return { cost, tokens };
}

function updateCostFromUsageMetadata(usageMetadata) {
  const normalized = parseUsageMetadata(usageMetadata);
  if (!normalized) return;
  const prompt = Number(normalized.prompt_tokens || 0);
  const completion = Number(normalized.completion_tokens || 0);
  const totalNewTokens = prompt + completion;
  if (totalNewTokens > 0) updateSessionTotalTokens(totalNewTokens);
  const costStats = normalized.cost_statistics || {};
  const costVal = costStats.total_cost_llm_api_usd || costStats.total_cost || 0;
  if (costVal && Number(costVal) > 0) updateSessionTotalCost(Number(costVal));
}

// Normalize various usage metadata shapes into a standard structure
function parseUsageMetadata(usageMetadata) {
  if (!usageMetadata || typeof usageMetadata !== 'object') return null;
  // Case 1: already flat
  if (typeof usageMetadata.prompt_tokens === 'number' || typeof usageMetadata.completion_tokens === 'number') {
    return {
      model: usageMetadata.model || '',
      prompt_tokens: usageMetadata.prompt_tokens || 0,
      completion_tokens: usageMetadata.completion_tokens || 0,
      total_tokens: usageMetadata.total_tokens || ((usageMetadata.prompt_tokens || 0) + (usageMetadata.completion_tokens || 0)),
      cost_statistics: usageMetadata.cost_statistics || null,
    };
  }

  // Case 2: nested under model key(s), e.g., { "vertex_ai/gemini-2.5-flash": { ... } }
  const keys = Object.keys(usageMetadata);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const v = usageMetadata[k];
    if (v && typeof v === 'object' && (typeof v.prompt_tokens === 'number' || typeof v.completion_tokens === 'number' || typeof v.total_tokens === 'number')) {
      return {
        model: k,
        prompt_tokens: v.prompt_tokens || 0,
        completion_tokens: v.completion_tokens || 0,
        total_tokens: v.total_tokens || ((v.prompt_tokens || 0) + (v.completion_tokens || 0)),
        cost_statistics: v.cost_statistics || usageMetadata.cost_statistics || null,
      };
    }
  }

  // Case 3: unknown shape
  return null;
}

// Reset per-session totals to zero and update UI
function resetSessionCostData() {
  const sessionId = getSessionIdFromUrlOrStore();
  const costStorageKey = `sessionTotalCost_${sessionId}`;
  const tokensStorageKey = `sessionTotalTokens_${sessionId}`;
  try {
    localStorage.setItem(costStorageKey, '0');
    localStorage.setItem(tokensStorageKey, '0');
  } catch (e) {
    if (DEBUG) console.warn('Failed resetting session cost data', e);
  }
  const totalCostElement = document.getElementById('total-cost');
  const totalTokensElement = document.getElementById('total-tokens');
  if (totalCostElement) totalCostElement.textContent = '$0.000';
  if (totalTokensElement) totalTokensElement.textContent = '0 tokens';
}

// --- Core API functions ---
async function sendQuery() {
  if (querySendInProgress) {
    if (DEBUG) console.log('Query already in progress');
    return;
  }
    
  const messageInput = document.querySelector('.chat-input-area .form-control');
  const query = messageInput.value.trim();
    
  if (query === '') {
    showAlert('Please enter a message');
    return;
  }
  
  if (!isConnected) {
    showAlert('Not connected to server. Please refresh the page.', 'error');
    return;
  }

  // Store the question for rendering later
  messageInput.dataset.lastQuestion = query;
  
  // Get the selected model from the dropdown
  const modelSelect = document.getElementById('model-select');
  const selectedModelCategory = sanitizeModelCategory(modelSelect.value);
  
  // Store the selected model in localStorage
  setModelCategoryInStore(selectedModelCategory);

  try {
    querySendInProgress = true;
    
    // Send question via WebSocket
    socket.emit('ask_question', {
      question: query,
      model_category: selectedModelCategory,
      session_id: getSessionIdFromUrlOrStore()
    });

  } catch (e) {
    console.error('Error in sendQuery:', e);
    showAlert('Error sending message: ' + e.message);
    unregisterRequestInProgress();
    querySendInProgress = false;
  }
}

// --- Session initialization function ---
async function initSession() {
  const sessionIdField = document.getElementById('session-id');
  const sessionId = sessionIdField.value.trim();
  
  if (sessionId === '') {
    showAlert('Please enter a session ID');
    return;
  }
  
  // Get current values to compare
  const currentStoredSessionId = localStorage.getItem('sessionId');
  const urlParams = new URLSearchParams(window.location.search);
  const currentSessionIdInUrl = urlParams.get('session_id');
  
  // Check if anything actually changed
  const needsUpdate = (sessionId !== currentStoredSessionId) || (sessionId !== currentSessionIdInUrl);
  
  if (needsUpdate) {
    // Update session ID in localStorage
    localStorage.setItem('sessionId', sessionId);
    
    // Check if URL needs to be updated
    if (currentSessionIdInUrl !== sessionId) {
      // Update URL with session ID and reload
      const url = new URL(window.location.href);
      url.searchParams.set('session_id', sessionId);
      
      window.location.href = url.toString();
      return; // Stop execution, page will reload
    }
  }
  
  // Clear chat for new session
  document.getElementById('chatMessages').innerHTML = '';
  
  // Load session cost data
  loadSessionCostData();
}

// --- Text area auto-resize function ---
function autoResizeTextarea(textarea) {
  // Reset height to auto to calculate the new height
  textarea.style.height = 'auto';
  
  // Set new height based on scrollHeight (with a min-height of one row)
  const newHeight = Math.max(textarea.scrollHeight, parseInt(window.getComputedStyle(textarea).lineHeight, 10));
  
  // Limit the max height
  const maxHeight = 100;
  textarea.style.height = Math.min(newHeight, maxHeight) + 'px';
  
  // Show/hide scrollbar based on content height
  textarea.style.overflowY = newHeight > maxHeight ? 'auto' : 'hidden';
}

// --- Session History Modal ---
function populateSessionHistoryModal() {
  const history = getSessionHistory();
  const listElement = document.getElementById('sessionHistoryList');
  if (!listElement) return;

  // Sort by last_seen_time descending
  history.sort((a, b) => new Date(b.last_seen_time) - new Date(a.last_seen_time));

  listElement.innerHTML = ''; // Clear existing items

  if (history.length === 0) {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = 'No session history recorded yet.';
    listElement.appendChild(li);
    return;
  }

  history.forEach(item => {
    const li = document.createElement('li');
    li.className = 'list-group-item';

    const link = document.createElement('a');
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', item.session_id);
    link.href = url.toString();
    link.className = 'session-history-link';
    link.textContent = item.session_id;
    
    // Make links open in the same tab (more intuitive for session switching)
    link.addEventListener('click', function(e) {
      e.preventDefault();
      window.location.href = this.href;
    });

    const details = document.createElement('small');
    details.className = 'd-block text-muted mt-1';
    details.textContent = `Created: ${new Date(item.created_time).toLocaleString()} | Last Seen: ${new Date(item.last_seen_time).toLocaleString()}`;

    li.appendChild(link);
    li.appendChild(details);
    listElement.appendChild(li);
  });
}

// --- Initialization and Event Listeners ---
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize sidebar collapse state
  applySidebarCollapseState();
  
  // Load session cost data
  loadSessionCostData();
  
  // Setup sidebar toggle button
  const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener('click', () => toggleSidebar());
  }
  
  // Initialize darkMode toggle
  const darkModeToggle = document.getElementById('darkModeToggle');
    
  // Set default for dark mode if not set
  let isDarkMode = localStorage.getItem('darkMode');
  if (isDarkMode === null) {
    isDarkMode = 'true';
    localStorage.setItem('darkMode', isDarkMode);
  }
  if (isDarkMode === 'true') {
    document.body.classList.add('dark-mode');
    if (darkModeToggle) {
      darkModeToggle.checked = true;
    }
  }
    
  // Listen for dark mode toggle changes
  if (darkModeToggle) {
    darkModeToggle.addEventListener('change', () => {
      if (darkModeToggle.checked) {
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'true');
      } else {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'false');
      }
      // Update the icon on the button
      updateDarkModeButtonIcon();
    });
  }
  
  // Set up the dark mode button
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  if (toggleDarkModeBtn) {
    toggleDarkModeBtn.addEventListener('click', toggleDarkMode);
    // Initialize button icon
    updateDarkModeButtonIcon();
  }
  
  // Initialize model selection from localStorage
  const modelSelect = document.getElementById('model-select');
  if (modelSelect) {
    const savedModelCategory = sanitizeModelCategory(getModelCategoryFromStore());
    setModelCategoryInStore(savedModelCategory);
    modelSelect.value = savedModelCategory;
    
    // Add event listener to save model changes
    modelSelect.addEventListener('change', function() {
      setModelCategoryInStore(sanitizeModelCategory(modelSelect.value));
    });
  }
  
  // Set up session history modal button and event
  const sessionHistoryBtn = document.getElementById('toggle-session-history-btn');
  const sessionHistoryModalElement = document.getElementById('sessionHistoryModal');
  if (sessionHistoryBtn && sessionHistoryModalElement) {
    // Using Bootstrap's event to populate modal just before it's shown
    sessionHistoryModalElement.addEventListener('show.bs.modal', function () {
      populateSessionHistoryModal();
      
      // Apply dark mode to the modal if needed
      const isDarkMode = localStorage.getItem('darkMode') === 'true';
      if (isDarkMode) {
        document.querySelectorAll('.modal-content, .list-group-item').forEach(element => {
          // Force dark mode classes to apply properly
          if (!element.classList.contains('dark-mode-element')) {
            element.classList.add('dark-mode-element');
          }
        });
      }
    });
  }
    
  // Set up help modal event for dark mode styling
  const helpModalElement = document.getElementById('helpModal');
  if (helpModalElement) {
    helpModalElement.addEventListener('show.bs.modal', function () {
      // Apply dark mode to the help modal if needed
      const isDarkMode = localStorage.getItem('darkMode') === 'true';
      if (isDarkMode) {
        // Ensure dark mode styling is applied to all modal elements
        const modalContent = this.querySelector('.modal-content');
        if (modalContent && !modalContent.classList.contains('dark-mode-applied')) {
          modalContent.classList.add('dark-mode-applied');
        }
      }
    });
  }
    
  // Initialize show LLM tool calls toggle
  const showLLMToolCalls = document.getElementById('showLLMToolCalls');
    
  // Set default for showLLMToolCalls if not set
  let showToolCalls = localStorage.getItem('showLLMToolCalls');
  if (showToolCalls === null) {
    showToolCalls = 'true';
    localStorage.setItem('showLLMToolCalls', showToolCalls);
  }
  if (showToolCalls === 'true') {
    showLLMToolCalls.checked = true;
    document.getElementById('toolUseSection').style.display = 'block';
  }
    
  // Listen for tool calls toggle changes
  showLLMToolCalls.addEventListener('change', () => {
    localStorage.setItem('showLLMToolCalls', showLLMToolCalls.checked);
    document.getElementById('toolUseSection').style.display = 
            showLLMToolCalls.checked ? 'block' : 'none';
  });
  
  // Initialize session ID from URL or localStorage
  const sessionIdField = document.getElementById('session-id');
  sessionIdField.value = getSessionIdFromUrlOrStore();
  
  // Add event listener for session ID field blur
  sessionIdField.addEventListener('blur', function() {
    const newSessionId = sessionIdField.value.trim();
    const currentSessionId = getSessionIdFromUrlOrStore();
    
    if (newSessionId) {
      // Only update and reload if the session ID has actually changed
      if (newSessionId !== currentSessionId) {
        addOrUpdateSessionInHistory(newSessionId);
        localStorage.setItem('sessionId', newSessionId);
        // Update URL with new session ID and reload page
        const url = new URL(window.location.href);
        url.searchParams.set('session_id', newSessionId);
        window.location.href = url.toString();
      }
      // If no change, do nothing
    } else {
      showAlert('Session ID cannot be empty.');
      // Revert to the previous value
      sessionIdField.value = currentSessionId;
    }
  });
  
  // Add event listener for increment button
  const incrementButton = document.getElementById('increment-button');
  if (incrementButton) {
    incrementButton.addEventListener('click', incrementSessionId);
  }
  
  // Setup chat functionality
  messageInput = document.querySelector('.chat-input-area .form-control');
  const sendButton = document.querySelector('.chat-input-area .btn');
    
  // Initialize textarea auto-resize
  autoResizeTextarea(messageInput);
  
  // Add input event for auto-resizing textarea as user types
  messageInput.addEventListener('input', function() {
    autoResizeTextarea(this);
  });
  
  // Event listeners for sending messages
  sendButton.addEventListener('click', sendQuery);
  
  // Updated keypress handler to handle Shift+Enter
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        // The default behavior will add a new line
      } else {
        // Submit with Enter (no shift)
        e.preventDefault();
        sendQuery();
      }
    }
  });
  
  // Initialize WebSocket connection
  initializeWebSocket();
  
  // Welcome message will be handled by displaySessionHistory function
  
  // Process auto-query from URL if present (after everything is initialized)
  setTimeout(() => {
    processAutoQuery();
  }, 1500);
});

// Utility function to safely parse JSON
function safeJsonParse(jsonString, defaultValue = {}) {
  if (!jsonString) return defaultValue;
  try {
    return JSON.parse(jsonString);
  } catch (e) {
    console.error('Error parsing JSON:', e);
    return defaultValue;
  }
}

// --- Session History Management ---
function getSessionHistory() {
  try {
    const historyJson = localStorage.getItem(SESSION_HISTORY_KEY);
    return historyJson ? JSON.parse(historyJson) : [];
  } catch (e) {
    console.error('Error reading session history from localStorage:', e);
    return [];
  }
}

function saveSessionHistory(history) {
  try {
    localStorage.setItem(SESSION_HISTORY_KEY, JSON.stringify(history));
  } catch (e) {
    console.error('Error saving session history to localStorage:', e);
  }
}

function addOrUpdateSessionInHistory(sessionId) {
  if (!sessionId) return;

  const history = getSessionHistory();
  const now = new Date().toISOString();
  const existingSessionIndex = history.findIndex(item => item.session_id === sessionId);

  if (existingSessionIndex > -1) {
    history[existingSessionIndex].last_seen_time = now;
  } else {
    history.push({
      session_id: sessionId,
      created_time: now,
      last_seen_time: now
    });
  }
  saveSessionHistory(history);
}
