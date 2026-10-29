type Entry = { value: unknown; updatedAt: number };

const cache = new Map<string, Entry>();
const pending = new Map<string, Promise<unknown>>();
export const RESOURCE_FRESH_MS = 5_000;
let generation = 0;

export function readResource<T>(key: string): { value: T; fresh: boolean } | null {
  const entry = cache.get(key);
  if (!entry) return null;
  return { value: entry.value as T, fresh: Date.now() - entry.updatedAt < RESOURCE_FRESH_MS };
}

export function writeResource<T>(key: string, value: T) {
  cache.set(key, { value, updatedAt: Date.now() });
}

export function clearResource(key: string) {
  cache.delete(key);
}

export function invalidateResources() {
  cache.clear();
  pending.clear();
  generation += 1;
}

export function requestResource<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const existing = pending.get(key);
  if (existing) return existing as Promise<T>;

  const startedAt = generation;
  const request = fetcher().then(value => {
    if (startedAt === generation) writeResource(key, value);
    return value;
  }).finally(() => { if (pending.get(key) === request) pending.delete(key); });
  pending.set(key, request);
  return request;
}
