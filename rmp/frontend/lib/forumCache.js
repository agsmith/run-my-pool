// Forum responses contain member-specific blocks and private moderation reports.
export function isForumRequest({ url }) {
  return /^\/(?:api\/)?messages(?:\/|$)/.test(url.pathname);
}
