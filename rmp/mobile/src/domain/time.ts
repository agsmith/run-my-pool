// Some legacy endpoints serialize UTC without an explicit timezone.
// Keep kickoff checks consistent with the API instead of using the phone's zone.
export function apiTime(value: string): number {
  return Date.parse(
    /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`,
  );
}
