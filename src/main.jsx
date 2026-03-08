import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import PoolDetectAI from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <PoolDetectAI />
  </StrictMode>
);
