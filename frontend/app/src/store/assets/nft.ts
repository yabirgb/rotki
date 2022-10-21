import { ActionResult } from '@rotki/common/lib/data';
import { MaybeRef } from '@vueuse/core';
import { ComputedRef } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { NftResponse } from '@/store/session/types';
import { useTasks } from '@/store/tasks';
import { AssetInfoWithId } from '@/types/assets';
import { NonFungibleBalance } from '@/types/nfbalances';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isNft } from '@/utils/nft';

/**
 * It is like {@link AssetInfoWithId} but with two extra properties for
 * NFTs. It contains an imageUrl (optional) which is the image associated
 * with the NFT and a collectionName (optional)
 */
export interface NftAsset extends AssetInfoWithId {
  imageUrl?: string;
  collectionName?: string;
}

export const useNftAssetInfoStore = defineStore('assets/nfts', () => {
  const { nonFungibleBalances } = storeToRefs(useNonFungibleBalancesStore());

  const toAsset = (balance: NonFungibleBalance): NftAsset => ({
    identifier: balance.id,
    symbol: balance.name ?? '',
    name: balance.name ?? '',
    imageUrl: balance.imageUrl ?? undefined,
    collectionName: balance.collectionName ?? undefined
  });

  const getNftDetails = (
    identifier: MaybeRef<string>
  ): ComputedRef<NftAsset | null> =>
    computed(() => {
      const id = get(identifier);

      if (!isNft(id)) {
        return null;
      }

      const balances = get(nonFungibleBalances);
      const balance = balances.find(item => item.id === id);

      if (!balance) {
        return null;
      }

      return toAsset(balance);
    });

  const searchNfts = (keyword: MaybeRef<string>): NftAsset[] => {
    const isAMatch = (field: string | null, search: string): boolean => {
      return !!field && field.toLocaleLowerCase().indexOf(search) >= 0;
    };
    const balances = get(nonFungibleBalances);
    const search = get(keyword).toLocaleLowerCase();
    const matches = balances.filter(({ collectionName, name }) => {
      return isAMatch(name, search) || isAMatch(collectionName, search);
    });

    return matches.map(toAsset);
  };

  const { awaitTask } = useTasks();
  const { t } = useI18n();

  const fetchNfts = async (
    ignoreCache: boolean
  ): Promise<ActionResult<NftResponse | null>> => {
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await api.fetchNfts(ignoreCache);
      const { result } = await awaitTask<NftResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.fetch_nfts.task.title').toString(),
          numericKeys: []
        }
      );
      return {
        result: NftResponse.parse(result),
        message: ''
      };
    } catch (e: any) {
      return {
        result: null,
        message: e.message
      };
    }
  };

  return {
    getNftDetails,
    fetchNfts,
    searchNfts
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNftAssetInfoStore, import.meta.hot)
  );
}
