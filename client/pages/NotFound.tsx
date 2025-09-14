import { useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="grid place-items-center p-10">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white">404</h1>
        <p className="mt-2 text-white/70">This page doesn't exist yet.</p>
        <a href="/" className="mt-4 inline-block rounded-lg bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90">
          Back to Home
        </a>
      </div>
    </div>
  );
};

export default NotFound;
