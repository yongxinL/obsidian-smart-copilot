import React, { useState, useEffect, ReactNode } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ChevronDown, ChevronRight, Folder, FileText, Command, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, CornerDownLeft } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidth?: string;
}

export function Modal({ isOpen, onClose, title, children, maxWidth = "max-w-lg" }: ModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-inverse-surface/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className={`relative w-full ${maxWidth} overflow-hidden rounded-2xl bg-surface-container-lowest shadow-2xl`}
          >
            <div className="flex items-center justify-between border-b border-surface-container-low px-6 py-4">
              <h3 className="font-headline text-lg font-bold text-on-surface">{title}</h3>
              <button
                onClick={onClose}
                className="rounded-full p-1 text-on-surface-variant hover:bg-surface-container-low transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

interface CommandPaletteMenuProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  items: {
    icon: ReactNode;
    label: string;
    rightLabel?: string;
    onClick: () => void;
    active?: boolean;
  }[];
}

export function CommandPaletteMenu({ isOpen, onClose, title, items }: CommandPaletteMenuProps) {
  const [selectedIndex, setSelectedIndex] = useState(-1);

  React.useEffect(() => {
    if (isOpen) {
      setSelectedIndex(-1);
    }
  }, [isOpen]);

  React.useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => (prev + 1) % items.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => (prev - 1 + items.length) % items.length);
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0 && items[selectedIndex]) {
            items[selectedIndex].onClick();
            onClose();
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, items, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-[99]" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            className="absolute bottom-full left-0 mb-4 w-[480px] max-w-[90vw] sm:max-w-[480px] bg-white/95 backdrop-blur-md border border-outline-variant/20 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.15)] z-[100] overflow-hidden"
          >
            <div className="p-2">
              {items.map((item, index) => {
                const isHovered = index === selectedIndex;
                const isActive = item.active && selectedIndex === -1;
                return (
                  <button
                    key={index}
                    onClick={() => {
                      item.onClick();
                      onClose();
                    }}
                    onMouseEnter={() => setSelectedIndex(index)}
                    onMouseLeave={() => setSelectedIndex(-1)}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all group ${
                      isHovered || isActive
                        ? 'bg-secondary/10 text-secondary'
                        : 'hover:bg-surface-container-low text-on-surface-variant hover:text-on-surface'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg transition-colors ${isHovered || isActive ? 'bg-secondary text-on-secondary' : 'bg-surface-container-low group-hover:bg-white'}`}>
                        {item.icon}
                      </div>
                      <span className="text-sm font-semibold">{item.label}</span>
                    </div>
                    {item.rightLabel && (
                      <span className="text-[10px] font-bold uppercase tracking-widest opacity-40">{item.rightLabel}</span>
                    )}
                  </button>
                );
              })}
            </div>

            <div className="bg-surface-container-lowest/80 border-t border-outline-variant/10 px-6 py-3 flex items-center justify-between">
              <span className="text-[10px] font-bold text-on-surface-variant/40 uppercase tracking-widest">{title}</span>
              <div className="flex items-center gap-4 text-[10px] font-bold text-on-surface-variant/40 uppercase tracking-widest">
                <div className="flex items-center gap-1">
                  <span className="px-1 py-0.5 bg-surface-container-low rounded text-[8px]">ESC</span>
                  <span>Close</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="flex flex-col -space-y-1">
                    <ArrowUp size={8} />
                    <ArrowDown size={8} />
                  </div>
                  <span>Select</span>
                </div>
                <div className="flex items-center gap-1">
                  <Command size={8} />
                  <CornerDownLeft size={8} />
                  <span>Confirm</span>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

interface AccordionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export function Accordion({ title, children, defaultOpen = false }: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-surface-container-low last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between py-4 text-left transition-colors hover:text-secondary"
      >
        <span className="font-headline text-sm font-bold uppercase tracking-widest">{title}</span>
        <motion.span
          animate={{ rotate: isOpen ? 0 : -90 }}
          className="text-on-surface-variant"
        >
          <ChevronDown size={16} />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="pb-4 text-sm text-on-surface-variant leading-relaxed">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface VaultItemProps {
  type: 'folder' | 'file';
  label: string;
  depth?: number;
  active?: boolean;
}

export function VaultItem({ type, label, depth = 0, active = false }: VaultItemProps) {
  return (
    <div 
      className={`flex items-center gap-2 py-1.5 px-3 rounded-lg cursor-pointer transition-colors group ${
        active ? 'bg-surface-container-high' : 'hover:bg-surface-container-high'
      }`}
      style={{ marginLeft: `${depth * 1.5}rem` }}
    >
      {type === 'folder' ? (
        <Folder size={14} className="text-on-surface-variant group-hover:text-secondary" />
      ) : (
        <FileText size={14} className="text-on-surface-variant group-hover:text-secondary" />
      )}
      <span className={`text-xs ${active ? 'text-secondary font-bold' : 'text-on-surface-variant'}`}>
        {label}
      </span>
    </div>
  );
}
