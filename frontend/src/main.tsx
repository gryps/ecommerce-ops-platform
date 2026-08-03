import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import HumanApp from "./HumanApp";
import "./human.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HumanApp />
  </StrictMode>,
);
