"use client";

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageContainer } from "@/components/layout/page-container";
import { siteConfig } from "@/config/site";
import { useMediaQuery } from "@/hooks/use-media-query";
import type { ResolvedSlide } from "@/lib/data/slides";
import { cn } from "@/lib/utils";

const AUTOPLAY_MS = 7000;

const arrowButton =
  "absolute top-1/2 z-10 flex size-10 -translate-y-1/2 items-center justify-center rounded-sm bg-masthead/85 text-masthead-foreground shadow-sm transition-colors outline-none hover:bg-masthead focus-visible:ring-3 focus-visible:ring-sedge/80 sm:size-11";

/** Teal caption pill; a fixed colour so the white text holds in both themes. */
const pill =
  "pointer-events-auto absolute z-10 hidden max-w-[70%] bg-[oklch(0.52_0.09_180/0.9)] py-1.5 leading-snug text-white shadow-md outline-none sm:block";

const stripButton =
  "flex size-8 items-center justify-center rounded-sm text-primary transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50";

/**
 * Full-width wetland image carousel. Site captions come from the Ramsar
 * Sites dataset via lib/data/slides.ts (resolved on the server).
 *
 * Autoplay is slow, pauses on hover/focus, can be paused explicitly, and
 * never starts when the viewer prefers reduced motion.
 */
export function WetlandCarousel({ slides }: { slides: ResolvedSlide[] }) {
  const [index, setIndex] = useState(0);
  const [userPlaying, setUserPlaying] = useState<boolean | null>(null);
  const [interacting, setInteracting] = useState(false);
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");

  const count = slides.length;
  const playing = count > 1 && (userPlaying ?? !reducedMotion);

  const go = useCallback((next: number) => setIndex((next + count) % count), [count]);

  useEffect(() => {
    if (!playing || interacting) return;
    const timer = window.setTimeout(() => go(index + 1), AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [playing, interacting, index, go]);

  if (count === 0) return null;
  const current = slides[index];
  const currentSubtitle = current.subtitle;

  const playToggle = (
    <button
      type="button"
      onClick={() => setUserPlaying(!playing)}
      aria-label={playing ? "Pause automatic slide show" : "Play automatic slide show"}
      className={stripButton}
    >
      {playing ? (
        <Pause className="size-4" aria-hidden="true" />
      ) : (
        <Play className="size-4" aria-hidden="true" />
      )}
    </button>
  );

  return (
    <section aria-label="Wetlands of India" className="bg-deep">
      <h1 className="sr-only">{siteConfig.name}</h1>
      <div
        role="region"
        aria-roledescription="carousel"
        aria-label="Wetland photographs"
        onMouseEnter={() => setInteracting(true)}
        onMouseLeave={() => setInteracting(false)}
        onFocus={() => setInteracting(true)}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setInteracting(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft") go(index - 1);
          if (event.key === "ArrowRight") go(index + 1);
        }}
      >
        <div className="relative h-[clamp(14rem,40vw,34rem)] overflow-hidden">
          {slides.map((slide, i) => {
            const active = i === index;
            const subtitle = slide.subtitle;
            return (
              <div
                key={slide.id}
                role="group"
                aria-roledescription="slide"
                aria-label={`${i + 1} of ${count}: ${slide.title}`}
                aria-hidden={!active}
                className={cn(
                  "absolute inset-0 transition-opacity duration-700 ease-out motion-reduce:transition-none",
                  active ? "visible opacity-100" : "invisible opacity-0",
                )}
              >
                <Image
                  src={slide.image}
                  alt={slide.alt}
                  fill
                  preload={i === 0}
                  sizes="100vw"
                  className={slide.fit === "contain" ? "object-contain" : "object-cover"}
                />

                {slide.credit ? (
                  <p className="absolute top-2 right-2 bg-black/55 px-2 py-0.5 text-[11px] text-white">
                    Photo: {slide.credit}
                  </p>
                ) : null}

                {/* Caption, from tablet up: name + state top-left, designation bottom-right */}
                {slide.href ? (
                  <Link
                    href={slide.href}
                    tabIndex={active ? undefined : -1}
                    aria-label={`${slide.title}${slide.state ? `, ${slide.state}` : ""} — view site profile`}
                    className={cn(
                      pill,
                      "top-4 left-0 rounded-r-full pr-6 pl-5 text-xl font-semibold transition-colors hover:bg-[oklch(0.44_0.09_180)] focus-visible:ring-3 focus-visible:ring-white/80 md:text-2xl",
                    )}
                  >
                    {slide.title}
                    {slide.state ? <span className="font-normal">, {slide.state}</span> : null}
                  </Link>
                ) : (
                  <p
                    className={cn(
                      pill,
                      "top-4 left-0 rounded-r-full pr-6 pl-5 text-xl font-semibold md:text-2xl",
                    )}
                  >
                    {slide.title}
                  </p>
                )}
                {subtitle ? (
                  <p
                    className={cn(
                      pill,
                      "right-0 bottom-14 rounded-l-full pr-5 pl-6 text-base md:text-lg",
                    )}
                  >
                    {subtitle}
                  </p>
                ) : null}
              </div>
            );
          })}

          {count > 1 ? (
            <>
              <button
                type="button"
                onClick={() => go(index - 1)}
                aria-label="Previous photograph"
                className={cn(arrowButton, "left-3 sm:left-5")}
              >
                <ChevronLeft className="size-5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => go(index + 1)}
                aria-label="Next photograph"
                className={cn(arrowButton, "right-3 sm:right-5")}
              >
                <ChevronRight className="size-5" aria-hidden="true" />
              </button>

              {/* Indicators + pause, overlaid bottom-centre from tablet up */}
              <PageContainer className="pointer-events-none absolute inset-x-0 bottom-3 hidden justify-center sm:flex">
                <div className="pointer-events-auto flex items-center gap-1 bg-card/95 px-2 py-1 shadow-sm">
                  <p className="px-1.5 text-sm text-muted-foreground tabular-nums md:hidden">
                    {index + 1} / {count}
                  </p>
                  <ul className="hidden items-center md:flex" aria-label="Choose photograph">
                    {slides.map((slide, i) => (
                      <li key={slide.id}>
                        <button
                          type="button"
                          onClick={() => go(i)}
                          aria-label={`Show photograph ${i + 1}: ${slide.title}`}
                          aria-current={i === index ? "true" : undefined}
                          className="group flex h-8 w-5 items-center justify-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50 md:w-6"
                        >
                          <span
                            aria-hidden="true"
                            className={cn(
                              "block h-1.5 w-3.5 transition-colors md:w-4",
                              i === index ? "bg-sedge" : "bg-primary/25 group-hover:bg-primary/50",
                            )}
                          />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <span aria-hidden="true" className="mx-1 h-5 border-l border-border" />
                  {playToggle}
                </div>
              </PageContainer>
            </>
          ) : null}
        </div>

        {/* Phone caption + controls */}
        <div className="flex items-center justify-between gap-3 border-b border-l-4 border-b-border border-l-sedge bg-card px-4 py-2.5 text-foreground sm:hidden">
          <div className="min-w-0">
            <p className="text-base leading-snug font-bold text-primary">
              {current.title}
              {current.state ? <span className="font-normal">, {current.state}</span> : null}
            </p>
            {currentSubtitle ? (
              <p className="mt-0.5 text-sm text-muted-foreground">{currentSubtitle}</p>
            ) : null}
          </div>
          {count > 1 ? (
            <div className="flex shrink-0 items-center gap-1">
              <p className="text-sm text-muted-foreground tabular-nums">
                {index + 1} / {count}
              </p>
              {playToggle}
            </div>
          ) : null}
        </div>

        <p
          className="sr-only"
          aria-live={playing && !interacting ? "off" : "polite"}
          aria-atomic="true"
        >
          {`Photograph ${index + 1} of ${count}: ${current.title}.${currentSubtitle ? ` ${currentSubtitle}.` : ""}`}
        </p>
      </div>
    </section>
  );
}
