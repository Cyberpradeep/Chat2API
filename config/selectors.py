"""
Centralized DOM Selectors for ChatGPT Web Interface.
Targets stable ARIA roles, data-testids, and UI text rather than volatile CSS classes.
"""

# Prompt Input Box (ProseMirror rich-text or standard textarea)
PROMPT_INPUT = [
    '#prompt-textarea',
    'div[id="prompt-textarea"][contenteditable="true"]',
    'div[role="textbox"]',
    'textarea#prompt-textarea'
]

# Send Button (Blue circle with upward arrow when text is entered)
SEND_BUTTON = [
    'button[data-testid="send-button"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label="Send message"]'
]

# Stop Generation Indicator (Appears during streaming)
STOP_BUTTON = [
    'button[data-testid="stop-button"]',
    'button[aria-label="Stop generating"]',
    'button[aria-label="Stop streaming"]'
]

# Think Mode Button (Inline on the right of the composer)
THINK_BUTTON = [
    'button:has-text("Think")',
    'button[aria-label*="Think"]',
    'button[data-testid="composer-think-button"]'
]

# Plus / Tools Button (Left side of prompt box, opens popup menu)
PLUS_BUTTON = [
    'button[aria-label="Create, upload, search and more"]',
    'button[aria-label*="Attach"]',
    'button[aria-label*="Add"]',
    'form button:has(svg):not([data-testid="send-button"]):not([data-testid="stop-button"])'
]

# Plus Menu Popup Items
WEB_SEARCH_ITEM = [
    'div[role="menuitem"]:has-text("Web search")',
    'button:has-text("Web search")',
    '[data-testid="web-search-item"]'
]

DEEP_RESEARCH_ITEM = [
    'div[role="menuitem"]:has-text("Deep research")',
    'button:has-text("Deep research")',
    '[data-testid="deep-research-item"]'
]

ADD_FILES_ITEM = [
    'div[role="menuitem"]:has-text("Add photos & files")',
    'button:has-text("Add photos & files")'
]

# Hidden File Input for attachments
FILE_INPUT = 'input[type="file"]'

# Upload loading indicator (attachment thumbnail progress)
FILE_LOADING_INDICATOR = [
    'div[data-testid="file-attachment-loading"]',
    '.file-attachment-loading',
    'svg.animate-spin'
]

# Assistant Message Turns
ASSISTANT_TURNS = [
    'div[data-message-author-role="assistant"]',
    'article:has([data-message-author-role="assistant"])',
    '[data-testid^="conversation-turn-"]:has([data-message-author-role="assistant"])'
]

# Prose / Markdown text containers
MARKDOWN_CONTAINERS = [
    '.markdown.prose',
    '.markdown',
    'div.prose'
]

# Collapsible Thought Process container
THOUGHT_CONTAINERS = [
    'div[data-testid="thought-process"]',
    'button:has-text("Thought for")',
    'button:has-text("Thinking for")',
    'details:has-text("Thought")'
]

# Web Search Sources / Citations
SOURCE_CONTAINERS = [
    'button:has-text("Sources")',
    'a[data-testid="web-search-citation"]',
    'a.citation'
]

# Common Modal Dismissals
DISMISS_MODALS = [
    'button[aria-label="Close"]',
    'button:has-text("Dismiss")',
    'button:has-text("Stay logged out")',
    'button:has-text("Okay, let\'s go")',
    'button:has-text("Accept all")',
    'button:has-text("Reject non-essential")'
]
