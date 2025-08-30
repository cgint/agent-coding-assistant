# DSPy Agent Results

## Question 1
**Question:** What are the different add-ons available for Campaign Orchestrator and what do they include?

**Answer:**
Campaign Orchestrator offers several add-ons, categorized as included, recurring, and one-off professional services:

**Included Add-ons (free until further notice):**
*   **Managed SaaS**: This add-on involves smec handling the client's account. It includes a certain number of scopes (target countries, webshops) depending on the Service Plan: 1 scope for Growth, 3 for Professional, and individually calculated for Enterprise. Microsoft Scopes do not count as additional scopes.

**Other Add-ons (recurring):**
*   **Strategic Consulting**: This includes the initial creation of a joint strategic roadmap in month 4, 5 hours of strategic consulting per year, and an Annual Business Review. It aims to establish smec as a strategic partner.
*   **Customer Success**: This add-on provides an additional 30-minute check-in per month, either maintaining the bi-weekly communication level from onboarding or adding monthly communication for another region.

**Professional Services (one-offs, if requested by the client):**
*   **Custom Analysis / Dashboard**: Creation of individual analyses and discussion of results, or the creation of a custom dashboard.
*   **Custom Data Import**: Includes custom offer extensions, supplemental feeds, custom inventory data import, or page feed customizations.
*   **Enhanced Conversions**: Utilizes first-party data to improve conversion tracking accuracy and bid optimization.
*   **Geo Split Test**: Covers Geo Split design, test setup, monitoring & reporting, and final analysis.
*   **Google IGAP Website Audit**: Requesting and utilizing an IGAP Website Audit from Google to provide website improvement recommendations.
*   **Market Entry Ad Strategy**: A one-off launch plan for a new geo-market to implement strategies for acquiring new customers (implementation not included).
*   **Microsoft Clarity for User Behavior**: Utilizes Microsoft Clarity to gain insights into user interactions on the client's website.
*   **Page Feed Setup (Base Setup)**: Setting up simple campaigns with Campaign Orchestrator to increase the share of wallet.
*   **Structured A/B Testing**: Creation of a testing roadmap and conducting 3 structured A/B tests for the client.
*   **Re-Setup of Campaign Structure**: Creation of an entirely new setup within the Campaign Orchestrator for the client.

📚 **Sources & References:**
• [Internal Knowledge Base](file://knowledge_base/internal_notes.md) - internal


🔍 **Search Queries Used:**
• "Internal Knowledge: Campaign Orchestrator add-ons"

**Tracked usage metadata:**
{'vertex_ai/gemini-2.5-flash': {'completion_tokens': 1511, 'prompt_tokens': 88423, 'total_tokens': 89934, 'completion_tokens_details': 0, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0, 'text_tokens': 88423, 'image_tokens': 0}}}

---
## Question 2
**Question:** How do I setup PMax campaigns with page feeds?

**Answer:**
Setting up and managing PMax campaigns with page feeds within the Campaign Orchestrator involves several steps, focusing on existing clients for wallet share expansion. The Page Feed approach aims to split PMax Shopping and PMax Non-shopping traffic for more granular steering, potentially increasing ROAS and MRR.

**Setup Options:**
*   **Option 1 (Base Setup):** Considers Product URLs + Landing Page Report URLs. This is the preferred option due to less effort required from Marketing Engineering (ME) and the client.
*   **Option 2 (Extended Setup):** Considers Product URLs + Custom Attribute URLs (with optional Landing Page Report URLs). This option requires more effort as the client must provide all desired URLs within Custom Attributes.

**Step-by-Step Guide:**

**1.) Requirement Check:**
*   The account or country must have at least **100 non-brand, non-shopping conversions** monthly. If fewer, Page Feeds are not suitable; consider a less advanced shopping and non-shopping PMax campaign split.

**2.) Concept Phase:**
*   **Page Feed Playbook Creation:** Use templates to create a playbook.
*   **Campaign Proposal Considerations:**
    *   **Brand Treatment:** Decide whether to exclude Brand from Page Feed campaigns if already separated.
    *   **Number of Page Feed campaigns:** Depends on monthly non-brand and non-shopping conversions:
        *   100 - 300 conversions: 3 campaigns (High, Low, Exploration)
        *   300+ - 600 conversions: 4 campaigns (High, Medium, Low, Exploration)
        *   600+ conversions: 5 campaigns (Super High, High, Medium, Low, Exploration)
*   **Playbook Pitch:** Client Team and Page Feed CSM pitch the concept to the client.

**3.) Contracting Phase:**
*   **Usage Fee:** A mandatory usage fee applies to PMax campaigns managed by smec for wallet share expansion.
*   **Setup / One-off Fee:**
    *   **Option 1 (Base Setup):** Free setup if minimum incremental spend of approx. €5,000/month is met; otherwise, a €2,080 setup fee applies.
    *   **Option 2 (Extended Setup):** Bill hours based on ME workload.

**4.) Setup Phase:**
*   **Business Logic Definition:**
    *   **Setup Type:** Define whether to use Option 1, Option 2, or a mix.
    *   **Performance Thresholds:** Define thresholds for assigning URLs to High, Medium, or Low Page Feeds based on Google Ads metrics or Orchestrator score.
    *   **Asset Group Logic:** Define how Asset Groups will be structured for each URL type.
    *   **Link to Platform:** Page Feeds will be linked to an existing Platform Scope.
*   **Jira Case Creation:** Create a Jira case detailing the setup.
*   **Page Feed Generation:** Marketing Engineering generates the page feeds (lead time of 4 weeks).
*   **Campaign Setup (Client CSM/PMM):**
    1.  **Check Page Feed Settings in Platform:** Ensure settings are active and billable.
    2.  **Customization of Generated Page Feeds:** Double-check for needed overrides, denylists, or allowlists via a Customisation Sheet.
    3.  **Set up Performance Max campaign in Google Ads UI:**
        *   Create a new PMax campaign *without* adding products from Merchant Center.
        *   Add the matching page feed.
        *   Enable Text Assets.
        *   Disable Final URL expansion for HI, ME, LO campaigns; enable for Exploration campaigns.
        *   Do not pause old Search/DSA campaigns immediately.
    4.  **Set up asset group structure:** Collect assets and use the Asset Group Setup Template, specifying URL rules using page feed custom labels.
    5.  **Add negative KWs and Brand Exclusions:** Brand exclusions can be done in campaign settings. CSS and GSE campaign negatives can be requested via Google forms.
    6.  **Register campaign IDs for invoicing:** Forward Account ID and campaign IDs to billing.

**5.) Campaign Management:**
*   **Monitoring:** Continuously monitor PMax Pagefeed campaigns, DSA-development, Search Terms, Landing Pages, Brand-development (if applicable), Display & Video Shares, and Quality of displayed ads.

**Microsoft PMax Campaigns with Page Feeds:**
For Microsoft PMax campaigns as part of the Campaign Orchestrator, prerequisites include using Google Merchant Center for Microsoft Ads. The setup involves calculating the performance score and populating the custom label in the merchant center. Campaign creation in Microsoft Ads is currently manual. The least complex option is using only Google performance data and the same score for both Microsoft PMax & Google PMax.

**tROAS and Budget Settings:**
*   Reduce frequency of significant changes (allow up to 2 weeks for Google's algorithm to learn).
*   Weekly updates for product assignments.
*   Change tROAS and significant Budget ideally not more than once every two weeks.
*   **Product Allocation (for a 3-way split):** Low score: max 40% of products; Mid score: around 50-55%; High score: 5-10%.
*   **Setting tROAS:** If the client goal is within +/- 10% of average ROAS, set tROAS goals accordingly. If more than 10% off, set tROAS goals according to the account average and increase over time.

📚 **Sources & References:**
• [Internal Knowledge Base](file://knowledge_base/internal_notes.md) - internal


🔍 **Search Queries Used:**
• "Internal Knowledge: setup PMax campaigns with page feeds"

**Tracked usage metadata:**
{'vertex_ai/gemini-2.5-flash': {'completion_tokens': 5478, 'prompt_tokens': 91602, 'total_tokens': 97080, 'completion_tokens_details': 0, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0, 'text_tokens': 91602, 'image_tokens': 0}}}

---
## Question 3
**Question:** What are the latest Google Ads feature updates announced in January 2025?

**Answer:**
For January 2025, Google will update its Political content policy.

Looking at the broader first quarter of 2025 and beyond, several other significant updates are planned for Google Ads:

**Q1 2025 (January - March):**
*   **Reporting Updates:** Campaign Manager 360 and Display & Video 360 will see reporting updates, including changes to reach report confidence default settings.
*   **Omnichannel Bidding:** This feature is expected to be introduced.
*   **Demand Gen Channel Controls:** In March 2025, channel controls for Demand Gen campaigns will expand to include YouTube, Discover, Gmail, and Google Display Network.
*   **Limited Ads 2.0:** On or after March 31, 2025, Limited ads and Technical ad delivery will be replaced by Limited ads 2.0.
*   **User Consent Requirement:** The requirement to re-obtain user consent every 13 months will be removed on or after March 25, 2025.

**Other Policy Updates in Early 2025:**
*   **February 2025:** Updates to Cryptocurrencies and related products policy, Gambling and Games Policy, and Google Publisher Policies.
*   **March 2025:** Updates to Regional Restriction Policies, Gambling and Games Policy, clarification of the Google Ads Review Process, Personalized ads policy, and the Dating and Companionship Ads policy.

**Later in 2025 (for context):**
*   **April 2025:** The option to create new Video Action Campaigns will be removed, with existing ones automatically upgrading to Demand Gen campaigns starting in July 2025. Updates to Healthcare and Medicines Policy, Industry-specific verification articles, Ads Transparency Policy, Google TV Masthead (format requirements), policy information related to account suspension, Unfair advantage policy, and Cryptocurrency Advertising Policy in the EU.
*   **May 2025:** Updates to the Personalized advertising policy, new display ads option for ad intents, and new settings for anchor ads and side rail ads.
*   **June 2025:** Advertisers will be able to edit the displayed payer name. Updates to the Verification Process for Debt Services and Google third-party policy. Additional ad technology vendors opt-out control will be deprecated.
*   **July 2025:** Updates to the Political content policy page and Election Ads verification page, and the Dangerous products or services policy.

Please note that specific feature announcements can evolve, and it's always recommended to check official Google Ads announcements for the most up-to-date information.

📚 **Sources & References:**
• [New features & announcements - Google Ads Help](https://support.google.com/google-ads/announcements/9048695?hl=en) - support.google.com
• [Driving better performance from AI-powered Search ads with ...](https://support.google.com/google-ads/answer/15967262?hl=en) - support.google.com
• [What's new in Google Analytics](https://support.google.com/analytics/answer/9164320?hl=en) - support.google.com
• [Updates to Ads Transparency Policy (April 2025) - Google Help](https://support.google.com/adspolicy/answer/16189141?hl=en) - support.google.com
• [Reporting updates in Q1 2025 - Campaign Manager 360 Help](https://support.google.com/campaignmanager/answer/15874746?hl=en) - support.google.com
• [Ad Manager policy change log - Google Help](https://support.google.com/admanager/answer/9385069?hl=en) - support.google.com


🔍 **Search Queries Used:**
• "Web Search: Google Ads feature updates January 2025"
• "Web Search: Google Ads updates 2025"

**Tracked usage metadata:**
{'vertex_ai/gemini-2.5-flash': {'completion_tokens': 1655, 'prompt_tokens': 18148, 'total_tokens': 19803, 'completion_tokens_details': 0, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0, 'text_tokens': 18148, 'image_tokens': 0}}, 'vertex_ai/gemini-2.5-flash-lite': {'completion_tokens': 26, 'prompt_tokens': 466, 'total_tokens': 492, 'completion_tokens_details': 0, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0, 'text_tokens': 466, 'image_tokens': 0}}}

---
