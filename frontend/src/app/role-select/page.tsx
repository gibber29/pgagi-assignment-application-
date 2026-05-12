"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiUrl } from "@/lib/api";

const roles = ["AI/ML Engineer", "Backend Engineer", "Data Scientist"];

export default function RoleSelect() {
  const [selectedRole, setSelectedRole] = useState<string>("");

  const handleStart = async () => {
    try {
      const response = await fetch(apiUrl("/api/interview/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: selectedRole }),
      });
      const data = await response.json();
      console.log(data);
      // Navigate to interview
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Select Your Target Role</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {roles.map((role) => (
              <Button
                key={role}
                variant={selectedRole === role ? "default" : "outline"}
                onClick={() => setSelectedRole(role)}
                className="h-16"
              >
                {role}
              </Button>
            ))}
          </div>
          <Button onClick={handleStart} disabled={!selectedRole} className="mt-4">
            Start Interview
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
