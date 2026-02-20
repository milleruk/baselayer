export function bindToggleGroup({
  root,
  buttonSelector,
  activeClasses = [],
  inactiveClasses = [],
  onChange,
  getValue = (btn) => btn.dataset.value
}) {
  const buttons = Array.from(root.querySelectorAll(buttonSelector));
  if (!buttons.length) return;

  function setActive(btn) {
    buttons.forEach(b => {
      b.classList.remove(...activeClasses);
      b.classList.add(...inactiveClasses);
      b.classList.remove('active');
    });
    btn.classList.add(...activeClasses);
    btn.classList.remove(...inactiveClasses);
    btn.classList.add('active');
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      setActive(btn);
      onChange?.(getValue(btn), btn);
    });
  });

  // ensure initial state is consistent
  const initial = buttons.find(b => b.classList.contains('active')) || buttons[0];
  setActive(initial);
  onChange?.(getValue(initial), initial);
}