/** Single source of motion — must match CSS beats in globals.css. */

export const easeOut = [0.2, 0.8, 0.2, 1] as const;

export const duration = {
  ack: 0.12,
  settle: 0.2,
  focus: 0.32,
  chapter: 0.56,
} as const;

export const softSpring = { type: "spring" as const, stiffness: 420, damping: 32, mass: 0.8 };

export const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.focus, ease: easeOut },
  },
};

export const fadeOnly = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: duration.settle, ease: easeOut },
  },
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.97 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: duration.settle, ease: easeOut },
  },
};

export const slideDrawer = {
  hidden: { x: "100%" },
  show: {
    x: 0,
    transition: { duration: duration.focus, ease: easeOut },
  },
  exit: {
    x: "100%",
    transition: { duration: duration.settle, ease: easeOut },
  },
};

export const pageEnter = {
  initial: { opacity: 0, y: 4 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.focus, ease: easeOut },
  },
};

export function stagger(delay = 0.04) {
  return {
    show: {
      transition: { staggerChildren: delay, delayChildren: 0.04 },
    },
  };
}
