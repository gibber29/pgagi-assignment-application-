import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">RAG Interview System</h1>
        <p className="text-lg mb-8">
          AI-powered candidate interview with retrieval-augmented generation.
        </p>
        <Link href="/interview">
          <Button size="lg">Start Interview</Button>
        </Link>
      </div>
    </div>
  );
}
