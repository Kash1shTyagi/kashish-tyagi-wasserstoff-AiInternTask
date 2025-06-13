import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="w-screen h-screen flex flex-col items-center justify-center bg-bgLight dark:bg-bgDark text-gray-900 dark:text-white">
      <h1 className="text-4xl font-bold mb-4">
        Document Research & Theme Chatbot
      </h1>
      <p className="mb-8 text-lg text-center max-w-xl">
        Ask questions across 75+ documents and get synthesized themes with citations.
      </p>
      <button
        onClick={() => navigate('/dashboard')}
        className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-blue-600 transition"
      >
        Get Started
      </button>
    </div>
  );
}