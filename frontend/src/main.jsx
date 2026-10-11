import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "./styles.css";

import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { Toaster } from "./components/ui/sonner";
import { AppProvider } from "./lib/app-store";

createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <BrowserRouter>
      <AppProvider>
        <App />
        <Toaster position="top-right" richColors />
      </AppProvider>
    </BrowserRouter>
  </ErrorBoundary>,
);
