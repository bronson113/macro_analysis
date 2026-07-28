import { useEffect, useRef } from 'react';

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

function getFocusableElements(dialog) {
  return [...dialog.querySelectorAll(focusableSelector)]
    .filter(element => !element.hasAttribute('hidden'));
}

export function useDialogFocus({ isOpen, onClose, dialogRef, initialFocusRef }) {
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen || !dialogRef.current) return undefined;

    const dialog = dialogRef.current;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const initialFocus = initialFocusRef.current || dialog;
    initialFocus.focus();

    const handleKeyDown = event => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== 'Tab') return;

      const focusableElements = getFocusableElements(dialog);
      if (!focusableElements.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const isOutsideDialog = !dialog.contains(document.activeElement);

      if (event.shiftKey && (isOutsideDialog || document.activeElement === firstElement)) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && (isOutsideDialog || document.activeElement === lastElement)) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (opener?.isConnected) opener.focus();
    };
  }, [isOpen, dialogRef, initialFocusRef]);
}
