const FORUM_PAGE_SIZE = 500;

export async function fetchAllForumMessages<T>(
  fetchPage: (skip: number, limit: number) => Promise<T[]>,
): Promise<T[]> {
  const messages: T[] = [];

  for (let skip = 0; ; skip += FORUM_PAGE_SIZE) {
    const page = await fetchPage(skip, FORUM_PAGE_SIZE);
    messages.push(...page);
    if (page.length < FORUM_PAGE_SIZE) return messages;
  }
}
