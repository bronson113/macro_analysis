export function getNextTabIndex({ key, currentIndex, tabCount }) {
  if (!tabCount) return null;

  if (key === 'ArrowRight') return (currentIndex + 1) % tabCount;
  if (key === 'ArrowLeft') return (currentIndex - 1 + tabCount) % tabCount;
  if (key === 'Home') return 0;
  if (key === 'End') return tabCount - 1;

  return null;
}
