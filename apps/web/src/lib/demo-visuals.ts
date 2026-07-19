export function demoProviderImage(providerSlug: string) {
  let hash = 2166136261;
  for (let index = 0; index < providerSlug.length; index += 1) {
    hash ^= providerSlug.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `/images/demo/provider-${String((Math.abs(hash) % 6) + 1).padStart(2, "0")}.png`;
}
