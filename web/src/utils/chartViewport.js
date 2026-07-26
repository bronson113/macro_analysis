const MIN_VIEWPORT_POINTS = 30;
const ZOOM_STEP = 0.1;
const PAN_STEP = 3;

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export const getWheelAnchorRatio = ({ clientX, left, width }) => {
  if (width <= 0) return 0.5;

  return clamp((clientX - left) / width, 0, 1);
};

export const createTrailingViewport = (requestedPoints, length) => {
  const end = length;
  const start = Math.max(length - requestedPoints, 0);
  return { start, end };
};

export const getVisibleViewport = (viewport, length) => {
  if (length <= 0) return { start: 0, end: 0 };

  const minWindow = Math.min(MIN_VIEWPORT_POINTS, length);
  const requestedWindow = Math.max(viewport.end - viewport.start, minWindow);
  const windowSize = Math.min(requestedWindow, length);
  const maxStart = length - windowSize;
  const start = clamp(viewport.start, 0, maxStart);

  return {
    start: Math.round(start),
    end: Math.round(start + windowSize),
  };
};

export const updateViewportWithWheel = ({
  viewport,
  length,
  deltaX = 0,
  deltaY = 0,
  anchorRatio = 0.5,
  panOnly = false,
}) => {
  if (length <= 0) return { start: 0, end: 0 };

  const current = getVisibleViewport(viewport, length);
  const currentWindow = current.end - current.start;
  const minWindow = Math.min(MIN_VIEWPORT_POINTS, length);

  if (panOnly || Math.abs(deltaX) > Math.abs(deltaY)) {
    const direction = deltaX || deltaY;
    const panBy = Math.round((direction / 120) * PAN_STEP * Math.max(currentWindow / 90, 1));
    return getVisibleViewport({ start: current.start + panBy, end: current.end + panBy }, length);
  }

  const zoomDirection = deltaY < 0 ? -1 : 1;
  const nextWindow = clamp(
    Math.round(currentWindow * (1 + zoomDirection * ZOOM_STEP)),
    minWindow,
    length
  );
  const safeAnchorRatio = clamp(anchorRatio, 0, 1);
  const anchorIndex = current.start + currentWindow * safeAnchorRatio;
  const nextStart = anchorIndex - nextWindow * safeAnchorRatio;

  return getVisibleViewport({ start: nextStart, end: nextStart + nextWindow }, length);
};
