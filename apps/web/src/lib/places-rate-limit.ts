type Bucket = { count: number; resetAt: number };

const buckets = new Map<string, Bucket>();
const windowMs = 60_000;
const requestLimit = 40;

export function consumePlacesQuota(key: string): boolean {
  const now = Date.now();
  const current = buckets.get(key);
  if (!current || current.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }
  if (current.count >= requestLimit) return false;
  current.count += 1;
  if (buckets.size > 5_000) {
    for (const [bucketKey, bucket] of buckets) if (bucket.resetAt <= now) buckets.delete(bucketKey);
  }
  return true;
}
