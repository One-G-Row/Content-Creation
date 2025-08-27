import React from 'react'
import { createRoot } from 'react-dom/client'
import AIAgent from './components/AIAgent'

// Ensure API base uses Vite env if provided
if (!import.meta.env.VITE_API_BASE) {
	// Default to localhost backend
	window.REACT_APP_API_BASE = 'http://localhost:8000'
}

createRoot(document.getElementById('root')).render(
	<React.StrictMode>
		<AIAgent />
	</React.StrictMode>
)