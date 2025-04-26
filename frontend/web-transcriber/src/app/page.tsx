// frontend/src/app/page.tsx
"use client"; // This page needs client-side interactivity

import React, { useState } from 'react';
import TranscriptionForm from '@/app/components/TranscriptionForm';

// Define specific analysis types (can be moved to a types file later)
interface SentimentResult {
    sentiment_label: string;
    sentiment_score: number;
}
interface PosCountsResult {
     pos_counts: { [key: string]: number }; // Example: { "NOUN": 10, "VERB": 5 }
}
interface WordFrequencyResult {
    word_frequency: { [key: string]: number }; // Example: { "hello": 3, "world": 2 }
}
interface TopicResult {
     topic: string;
}

interface AnalysisStructure {
    sentiment: SentimentResult | null;
    pos_counts: PosCountsResult | null;
    word_frequency: WordFrequencyResult | null;
    topic: TopicResult | null;
}


// Define structure for API response (matching backend's TranscriptionResponse)
interface ApiResponse {
    message: string;
    transcription: string | null;
    srt_transcription: string | null;
    analysis: AnalysisStructure  | null; 
    original_url: string;
    time_range: string;
    download_seconds?: number;
    transcription_seconds?: number;
    total_seconds?: number;
}

export default function Home() {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<ApiResponse | null>(null);

    const handleFormSubmit = async (formData: { videoUrl: string; startTime: string; endTime: string }) => {
        setIsLoading(true);
        setError(null);
        setResult(null); // Clear previous results

        console.log("Form submitted:", formData);

        // --- API Call ---
        try {
            // IMPORTANT: Replace with your actual backend URL when running
            // If backend runs on http://localhost:8000
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/transcribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json', // Explicitly accept JSON
                },
                body: JSON.stringify({
                    video_url: formData.videoUrl,
                    start_time: formData.startTime,
                    end_time: formData.endTime,
                    generate_srt: true, // Always request SRT for now
                    // Add analysis flags if you want UI controls for them later
                    analyze_sentiment: false,
                    analyze_pos: false,
                    analyze_word_frequency: false,
                    analyze_topic: false,
                }),
            });

            const responseData = await response.json();

            if (!response.ok) {
                // Try to get error detail from backend response, fallback otherwise
                const errorDetail = responseData.detail || `Request failed with status ${response.status}`;
                throw new Error(errorDetail);
            }

            console.log("API Response:", responseData);
            setResult(responseData as ApiResponse);

        } catch (err: unknown) { 
            console.error("API Error:", err);
            let errorMessage = "An error occurred while contacting the API.";
            if (err instanceof Error) {
                
                errorMessage = err.message;
            } else if (typeof err === 'string') {
                 errorMessage = err;
            }
            // Potentially handle other error types if necessary
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
        // --- End API Call ---
    };

    return (
        <main className="flex min-h-screen flex-col items-center justify-start p-6 md:p-12 bg-gray-900 text-gray-100">
            <div className="w-full max-w-2xl">
                <h1 className="text-3xl font-bold mb-6 text-center text-white">
                    Video Segment Transcriber
                </h1>

                <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
                    <TranscriptionForm onSubmit={handleFormSubmit} isLoading={isLoading} />
                </div>

                {/* --- Display Area --- */}
                {/* Error Display */}
                 {error && !isLoading && (
                    <div className="mt-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <strong className="font-bold">Error: </strong>
                        <span className="block sm:inline">{error}</span>
                    </div>
                )}

                {/* Loading Indicator */}
                {isLoading && (
                    <div className="mt-6 text-center">
                         <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto"></div>
                         <p className="mt-2 text-gray-400">Processing, please wait...</p>
                    </div>
                )}

                {/* Results Display */}
                {result && !isLoading && (
                    <div className="mt-6 bg-gray-800 p-6 rounded-lg shadow-lg">
                        <h2 className="text-2xl font-semibold mb-4 text-white">Transcription Results</h2>
                        <div className="space-y-4">
                            <div>
                                <h3 className="text-lg font-medium text-gray-300 mb-1">Plain Text:</h3>
                                <pre className="bg-gray-700 p-3 rounded text-sm text-gray-200 whitespace-pre-wrap break-words">
                                    {result.transcription || "No text transcribed."}
                                </pre>
                            </div>
                            {result.srt_transcription && (
                                 <div>
                                    <h3 className="text-lg font-medium text-gray-300 mb-1">SRT Format:</h3>
                                    <pre className="bg-gray-700 p-3 rounded text-sm text-gray-200 max-h-60 overflow-y-auto whitespace-pre-wrap break-words">
                                        {result.srt_transcription}
                                    </pre>
                                </div>
                            )}
                            <div className="text-xs text-gray-400 pt-2 border-t border-gray-700 mt-4">
                                <p>Original URL: {result.original_url}</p>
                                <p>Time Range: {result.time_range}</p>
                                 {result.total_seconds !== undefined && (
                                    <p>Processing Time: {result.total_seconds.toFixed(2)}s
                                        (Download: {result.download_seconds?.toFixed(2)}s,
                                         Transcription: {result.transcription_seconds?.toFixed(2)}s)
                                    </p>
                                 )}
                            </div>
                        </div>
                    </div>
                )}
                {/* --- End Display Area --- */}

            </div>
        </main>
    );
}