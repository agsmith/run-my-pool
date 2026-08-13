export function nextDefaultEntryName(entries = []) {
  const usedNames = new Set(
    entries.map((entry) => String(entry?.name || '').trim().toLowerCase()),
  );
  let number = 1;
  while (usedNames.has(`entry ${number}`)) number += 1;
  return `Entry ${number}`;
}
