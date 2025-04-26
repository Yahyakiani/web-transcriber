// frontend/src/components/TranscriptionForm.tsx
"use client"; // Required for components with interactivity (hooks like useState, onClick)

import React, { useState } from 'react';

// Define the structure for the form data
interface FormData {
    videoUrl: string;
    startTime: string;
    endTime: string;
}

// Define the props expected by the component, including the onSubmit handler
interface TranscriptionFormProps {
    onSubmit: (data: FormData) => void; // Function to call when form is submitted
    isLoading: boolean; // To disable button during processing
}

const TranscriptionForm: React.FC<TranscriptionFormProps> = ({ onSubmit, isLoading }) => {
    const [formData, setFormData] = useState<FormData>({
        videoUrl: '',
        startTime: '',
        endTime: '',
    });
    const [error, setError] = useState<string | null>(null);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault(); // Prevent default form submission (page reload)
        setError(null); // Clear previous errors

        // Basic validation
        if (!formData.videoUrl || !formData.startTime || !formData.endTime) {
            setError("Please fill in all fields.");
            return;
        }
        // Rudimentary time format check (can be improved)
        const timeRegex = /^(\d{1,2}:)?\d{1,2}:\d{2}$/;
        if (!timeRegex.test(formData.startTime) || !timeRegex.test(formData.endTime)) {
            setError("Please use format HH:MM:SS or MM:SS for time.");
            return;
        }
        // Basic URL check (browser built-in validation helps, but check non-empty)
         try {
           new URL(formData.videoUrl);
         } catch (_) {
           setError("Please enter a valid URL.");
           return;
         }

        onSubmit(formData); // Call the parent component's submit handler
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
             {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                    <span className="block sm:inline">{error}</span>
                </div>
            )}
            <div>
                <label htmlFor="videoUrl" className="block text-sm font-medium text-gray-300 mb-1">
                    Video URL
                </label>
                <input
                    type="url" // Use type="url" for basic browser validation
                    name="videoUrl"
                    id="videoUrl"
                    value={formData.videoUrl}
                    onChange={handleChange}
                    required // HTML5 validation
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="https://www.youtube.com/watch?v=..."
                    disabled={isLoading}
                />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label htmlFor="startTime" className="block text-sm font-medium text-gray-300 mb-1">
                        Start Time (e.g., 1:05 or 00:30)
                    </label>
                    <input
                        type="text"
                        name="startTime"
                        id="startTime"
                        value={formData.startTime}
                        onChange={handleChange}
                        required
                        pattern="^(\d{1,2}:)?\d{1,2}:\d{2}$" // HTML5 pattern validation
                        title="Format: HH:MM:SS or MM:SS"
                         className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="0:15"
                        disabled={isLoading}
                    />
                </div>
                <div>
                    <label htmlFor="endTime" className="block text-sm font-medium text-gray-300 mb-1">
                        End Time (e.g., 1:45 or 02:00)
                    </label>
                    <input
                        type="text"
                        name="endTime"
                        id="endTime"
                        value={formData.endTime}
                        onChange={handleChange}
                        required
                        pattern="^(\d{1,2}:)?\d{1,2}:\d{2}$"
                        title="Format: HH:MM:SS or MM:SS"
                         className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="1:30"
                        disabled={isLoading}
                    />
                </div>
            </div>
            <div>
                <button
                    type="submit"
                    disabled={isLoading}
                    className={`w-full px-4 py-2 font-semibold rounded-md transition-colors duration-200 ease-in-out ${
                        isLoading
                            ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                            : 'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900'
                    }`}
                >
                    {isLoading ? 'Processing...' : 'Transcribe Segment'}
                </button>
            </div>
        </form>
    );
};

export default TranscriptionForm;