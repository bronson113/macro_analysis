export function buildMarkdownUrl(basePath, filename, cacheBuster) {
  const normalizedBasePath = basePath.replace(/\/+$/, '');
  const normalizedFilename = filename.replace(/^\/+/, '');
  return `${normalizedBasePath}/${normalizedFilename}?t=${cacheBuster}`;
}
