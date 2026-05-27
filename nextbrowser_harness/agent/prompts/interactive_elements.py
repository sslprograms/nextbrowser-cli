"""
Guidance for handling interactive elements across common platforms.

Ported from next-browser-main/task-runner — tells the AI how to handle
contenteditable divs, dropdowns, rich text editors, and platform-specific
element patterns (Facebook, LinkedIn, Twitter/X, Reddit, etc.).
"""

INTERACTIVE_ELEMENTS_GUIDANCE = """
<interactive_element_guidance>
**CRITICAL: Enhanced Interactive Element Handling**

When dealing with interactive elements like chat boxes, message inputs, or form fields, follow these strategies:

**1. Message/Chat Input Fields:**
- Look for elements with types: `input`, `textarea`, `div[contenteditable="true"]`, `p[contenteditable="true"]`
- For rich text editors, the actual input might be a child element (indented with \\t)
- Try clicking the parent container first, then input into the child element
- Common patterns: `[parent_index]<div>Message input</div>` with `\\t[child_index]<p>Type a message...</p>`

**2. Form Field Strategy:**
- If `input_text` fails on an element, try `click_element_by_index` first to focus it
- For complex inputs, try the parent element if the child element fails
- Use `send_keys` as a fallback when `input_text` doesn't work

**3. Element Selection Priority:**
- **First choice**: Direct input elements (`input`, `textarea`)
- **Second choice**: Contenteditable containers (`div[contenteditable]`, `p[contenteditable]`)
- **Third choice**: Child elements of interactive containers
- **Last resort**: Use `send_keys` with specific key sequences

**4. Retry Strategy for Interactive Elements:**
- If an action fails, analyze the element structure in the browser state
- Try different interaction methods: `click_element_by_index` -> `input_text` -> `send_keys`
- Check if the element changed or new elements appeared after the failed action
- Don't give up after 2-3 failures - try alternative approaches

**5. Common Interactive Element Patterns:**
- **Search bars**: Usually `input[type="text"]` or `input[type="search"]`
- **Form submissions**: Look for `button[type="submit"]` or similar submit buttons
- **Dropdowns**: May require `click_element_by_index` to open, then select options
- **Facebook interactions**:
  - Message inputs use `div[contenteditable="true"]` with nested `p` or `span` elements
  - Post reactions (Like, Love, Haha, etc.) are often `div[aria-label*="reaction"]` elements
  - Comment boxes appear after clicking "Comment" and use similar contenteditable divs
  - Follow buttons are usually stable `button[type="submit"]` elements
  - Story interactions require clicking on story circles at the top of the feed
  - Marketplace listings have "Message" buttons that open chat interfaces
- **LinkedIn interactions**:
  - Post composition uses `div[data-testid="post-comment-box"]` or `div[contenteditable="true"]`
  - Connection requests are `button[aria-label*="Connect"]` or similar
  - Message inputs in chat use `div[data-testid="msg-form__message-input"]` with contenteditable
  - Post reactions are `button[aria-label*="react"]` elements
  - Job applications often have "Easy Apply" buttons that open forms
- **Twitter/X interactions**:
  - Like/Repost/Reply buttons often change indices when scrolling or when new content loads
  - Follow buttons in "You might like" sections are usually more stable
  - Tweet composition uses `div[data-testid="tweetTextarea_0"]` or similar contenteditable elements
  - Post interactions may require scrolling to find the right post first
- **Reddit interactions**:
  - Login form uses standard `input[type="text"]` and `input[type="password"]`
  - Post creation uses contenteditable rich text editors
  - Comment boxes appear after clicking reply
  - Upvote/downvote buttons are `button[aria-label*="upvote"]` or similar

**6. When Actions Fail:**
- Analyze the error message and element state
- Check if the page changed or new elements appeared
- Try scrolling to reveal more context
- Use `extract_structured_data` to get a complete page view if needed
- Consider if the element requires a different interaction pattern

**7. CRITICAL: Element Not Found Error Handling:**
- When you get "Element not found" errors, DO NOT keep trying the same element
- The element may have moved, been removed, or requires different interaction
- Try these steps in order:
  1. Scroll the page to see if the element is off-screen
  2. Look for similar elements with different indices
  3. Check if the page layout changed (new elements appeared)
  4. Try alternative approaches
  5. If all else fails, move to the next task item rather than getting stuck
</interactive_element_guidance>
"""
