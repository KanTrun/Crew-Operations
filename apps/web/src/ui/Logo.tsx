"use client";

import { motion } from "framer-motion";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <motion.svg
        width="40"
        height="40"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
        initial="hidden"
        animate="visible"
        whileHover="hover"
      >
        {/* Outer Ring */}
        <motion.circle
          cx="50"
          cy="50"
          r="45"
          stroke="var(--nq-copper)"
          strokeWidth="2"
          strokeDasharray="4 8"
          className="will-change-transform-opacity"
          variants={{
            hidden: { pathLength: 0, rotate: -90, opacity: 0 },
            visible: { 
              pathLength: 1, 
              rotate: 0, 
              opacity: 1,
              transition: { duration: 2, ease: "easeInOut" }
            },
            hover: {
              rotate: 180,
              strokeWidth: 4,
              transition: { duration: 1, ease: "linear", repeat: Infinity }
            }
          }}
        />
        
        {/* Inner Geometric Shape (N & Q abstract) */}
        <motion.path
          d="M 30 70 L 30 30 L 50 70 L 70 30 L 70 70"
          stroke="var(--nq-fg)"
          strokeWidth="6"
          strokeLinecap="square"
          strokeLinejoin="miter"
          className="will-change-transform-opacity"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: { 
              pathLength: 1, 
              opacity: 1,
              transition: { duration: 1.5, ease: "circOut", delay: 0.5 }
            },
            hover: {
              stroke: "var(--nq-copper)",
              scale: 1.1,
              transition: { duration: 0.3 }
            }
          }}
        />

        {/* Center Dot (The "Pulse/Nhip") */}
        <motion.circle
          cx="50"
          cy="50"
          r="6"
          fill="var(--nq-red)"
          className="will-change-transform-opacity"
          variants={{
            hidden: { scale: 0, opacity: 0 },
            visible: { 
              scale: [1, 1.5, 1],
              opacity: 1,
              transition: { 
                duration: 2, 
                repeat: Infinity, 
                ease: "easeInOut",
                delay: 1
              }
            },
            hover: {
              scale: 2,
              fill: "var(--nq-copper)",
              transition: { duration: 0.3 }
            }
          }}
        />
      </motion.svg>
      <div className="ml-3 flex flex-col justify-center overflow-hidden">
        <motion.span 
          className="text-xl font-black uppercase tracking-tighter leading-none text-[var(--nq-fg)]"
          variants={{
            hidden: { y: 20, opacity: 0 },
            visible: { y: 0, opacity: 1, transition: { duration: 0.5, delay: 0.8 } }
          }}
          initial="hidden"
          animate="visible"
        >
          NHỊP QUÁN
        </motion.span>
        <motion.span 
          className="text-[10px] font-mono uppercase tracking-[0.3em] text-[var(--nq-copper)] leading-none mt-1"
          variants={{
            hidden: { x: -20, opacity: 0 },
            visible: { x: 0, opacity: 1, transition: { duration: 0.5, delay: 1 } }
          }}
          initial="hidden"
          animate="visible"
        >
          Digital System
        </motion.span>
      </div>
    </div>
  );
}
