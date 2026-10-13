"use client";

import { Minus, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface MapControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
}

export function MapControls({ onZoomIn, onZoomOut }: MapControlsProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border bg-background/95 p-1 shadow-sm">
      <Button variant="ghost" size="icon" onClick={onZoomIn} aria-label="Zoom in">
        <Plus className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onZoomOut} aria-label="Zoom out">
        <Minus className="h-4 w-4" />
      </Button>
    </div>
  );
}
