import { SupportedAsset } from '@/services/types-model';

export interface AssetState {}

export interface AssetDBVersion {
  readonly local: number;
  readonly remote: number;
  readonly newChanges: number;
}

export interface AssetUpdateCheckResult {
  readonly updateAvailable: boolean;
  readonly versions?: AssetDBVersion;
}

export interface AssetUpdateConflictResult {
  readonly identifier: string;
  readonly local: SupportedAsset;
  readonly remote: SupportedAsset;
}

export type AssetUpdateResult = AssetUpdateConflictResult[] | boolean;

export interface ApplyUpdateResult {
  readonly done: boolean;
  readonly conflicts?: AssetUpdateConflictResult[];
}
