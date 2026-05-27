"""
Reddit-specific agent guidance (ported from next-browser-main interactive_elements).

Use when task or URL involves reddit.com — scroll feeds, open comment boxes, submit.
"""

REDDIT_GUIDANCE = """
<reddit_automation>
**Reddit feeds and comments**

1. **Find the post first** — posts below the fold are NOT in the initial element list.
   Use the `scroll` action with `num_pages` (e.g. 0.5, 1.0, 2.0) until the post title or subreddit thread is visible in <browser_state> or <browser_vision>.

2. **Open the comment box** — click the post title or "Comment" / comment icon on that post.
   New elements appear (*[N] markers). Re-read state before typing.

3. **Type the comment** — often a `div[contenteditable="true"]` or nested `p` child (indented under a parent index).
   If `input_text` fails: `click_element_by_index` on the parent, then `input_text` on the child, then `send_keys` as fallback.

4. **Submit** — click "Comment" / "Reply" submit button after text is entered; verify the comment appears or the box clears.

5. **SPA behavior** — indices change after scroll and after opening comment UI. Never reuse stale [N] from a previous step without a fresh `state`.

6. **Do not claim success** until you see evidence in browser state/screenshot (comment visible, or success toast).

Recommended action sequence for "comment on a post":
  scroll (num_pages) -> click_element_by_index (post or comment) -> state -> input_text -> click_element_by_index (submit) -> state -> done
</reddit_automation>
"""
