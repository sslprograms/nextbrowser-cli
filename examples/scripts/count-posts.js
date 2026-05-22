// Run in page via: nextbrowser exec https://www.reddit.com --js-file examples/scripts/count-posts.js
(() => {
  const n = document.querySelectorAll(
    "article, [data-testid='post-container'], .Post"
  ).length;
  return { postNodes: n, href: location.href, title: document.title };
})();
