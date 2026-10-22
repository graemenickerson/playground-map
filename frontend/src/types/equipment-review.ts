import { z } from "zod";

export const ReviewLocationSchema = z.object({
  type: z.literal("Point"),
  coordinates: z.tuple([
    z.number().min(-180).max(180),
    z.number().min(-90).max(90),
  ]),
});

export const EquipmentReviewSchema = z.object({
  equipmentId: z.string().uuid(),
  sourceRecordId: z.string().min(1),
  location: z.unknown(),
  reason: z.enum([
    "invalid_location",
    "no_park_match",
    "multiple_park_matches",
    "group_contains_assigned_equipment",
    "group_validation_failed",
  ]),
  details: z.string().optional(),
});

export const EquipmentReviewListSchema = z.array(
  EquipmentReviewSchema,
);

export type EquipmentReview = z.infer<
  typeof EquipmentReviewSchema
>;
