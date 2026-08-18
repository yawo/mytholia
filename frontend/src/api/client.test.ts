import { afterEach, describe, expect, it, vi } from "vitest";
import { generatePodcast } from "./client";

describe("API client locale headers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sends Accept-Language when generating a podcast", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        corpus_id: "test-corpus",
        entity_id: "char_hero",
        script: "Récit français.",
        audio_url: null,
        length_seconds: 180,
        engine: "deepgram",
        available_engines: ["deepgram"],
        cached: false,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await generatePodcast("test-corpus", "char_hero", undefined, false, "deepgram", "fr");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/podcast",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "Accept-Language": "fr",
        }),
      })
    );
  });
});
