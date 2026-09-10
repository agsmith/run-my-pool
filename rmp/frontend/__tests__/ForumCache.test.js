import { isForumRequest } from '../lib/forumCache';

test.each(['/messages/pool/one', '/messages/pool/one/safety', '/messages/blocks/user', '/api/messages/pool/one/safety'])(
  'keeps private Forum responses out of offline caches: %s', path => {
    expect(isForumRequest({ url: new URL(path, 'https://runmypool.net') })).toBe(true);
  },
);
test.each(['/pool/one/messages', '/messages-logo.png', '/icons/icon.png', '/privacy'])(
  'preserves normal routing for %s', path => {
    expect(isForumRequest({ url: new URL(path, 'https://runmypool.net') })).toBe(false);
  },
);
