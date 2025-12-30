import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AlertTriangle, Clapperboard, X } from 'lucide-react';
import { ProcessingPage, ResultPage, UploadPage } from './components';
import { useAppStore } from './store/appStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function AppContent() {
  const { step, error, setError } = useAppStore();

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <Clapperboard className="w-8 h-8 text-indigo-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 leading-none">
                DubWizard
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                AI-powered video dubbing
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Global Error Banner */}
        {error && step !== 'processing' && (
          <div className="max-w-2xl mx-auto mb-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
              <AlertTriangle className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-700">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600 transition-colors"
                aria-label="Close error"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Step Content */}
        {step === 'upload' && <UploadPage />}
        {step === 'processing' && <ProcessingPage />}
        {step === 'result' && <ResultPage />}
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-sm text-gray-400">
        <p>DubWizard - English to Hindi video dubbing</p>
        <p className="mt-1">Max 60 second videos | MP4 format only</p>
      </footer>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
