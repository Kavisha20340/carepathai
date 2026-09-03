import React, { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';

export default function ConversationDisplay() {
  const { conversationHistory } = useStore();
  const containerRef = useRef(null);

  // Directly adjust container scrollTop to prevent global window/viewport scrolling
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [conversationHistory]);

  return (
    <div 
      ref={containerRef}
      className="w-full flex flex-col gap-4 p-4 max-h-[300px] min-h-[100px] h-auto overflow-y-auto bg-gray-50/50 dark:bg-gray-900/15"
    >
      {conversationHistory.map((msg, index) => {
        const isUser = msg.role === 'user';
        const isGreeting = index === 0;

        return (
          <div
            key={index}
            className={`flex flex-col max-w-[85%] ${
              isGreeting 
                ? 'self-center items-center text-center max-w-lg' 
                : (isUser ? 'self-end items-end' : 'self-start items-start')
            }`}
          >
            <div
              className={`px-4 py-3 rounded-2xl text-base leading-relaxed border ${
                isGreeting
                  ? 'bg-white dark:bg-gray-800 text-gray-850 dark:text-gray-200 border-gray-100 dark:border-gray-700 shadow-sm font-medium text-center'
                  : (isUser
                    ? 'bg-indigo-600 text-white rounded-br-none border-transparent shadow-sm'
                    : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-none border-gray-100 dark:border-gray-700 shadow-sm')
              }`}
            >
              {msg.text}
            </div>
            {!isGreeting && (
              <span className="text-[10px] text-gray-400 mt-1 px-1 font-semibold">
                {new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}