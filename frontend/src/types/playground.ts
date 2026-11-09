import { z } from "zod";

export const SiteTypeSchema = z.enum([
  "park",
  "popup",
  "school",
  "unknown",
]);

export type SiteType = z.infer<typeof SiteTypeSchema>;

export const AgeRangeSchema = z.enum(["2-5", "5-12"]);

export type AgeRange = z.infer<typeof AgeRangeSchema>;

export const PlaygroundFiltersSchema = z.object({
  q: z.string().trim().max(100),
  age: AgeRangeSchema.nullable(),
  washroom: z.boolean(),
});

export type PlaygroundFilters = z.infer<
  typeof PlaygroundFiltersSchema
>;

export const PlaygroundSchema = z.object({
  _id: z.string().uuid(),
  name: z.string().min(1).nullable(),
  siteType: SiteTypeSchema,
  location: z.object({
    type: z.literal("Point"),
    coordinates: z.tuple([
      z.number().min(-180).max(180),
      z.number().min(-90).max(90),
    ]),
  }),
  parkSourceId: z.string().uuid().nullable(),
});

export const PlaygroundListSchema = z.object({
  items: z.array(PlaygroundSchema),
  limit: z.number().int().min(1).max(500),
  hasMore: z.boolean(),
});

export type Playground = z.infer<typeof PlaygroundSchema>;
export type PlaygroundList = z.infer<typeof PlaygroundListSchema>;
