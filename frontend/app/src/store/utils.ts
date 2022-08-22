import { Message, Severity } from '@rotki/common/lib/messages';
import { Ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import * as logger from 'loglevel';
import i18n from '@/i18n';
import { Section, Status } from '@/store/const';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { FetchData } from '@/store/typing';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export async function fetchDataAsync<T extends TaskMeta, R>(
  data: FetchData<T, R>,
  state: Ref<R>
): Promise<void> {
  if (
    !get(data.state.activeModules).includes(data.requires.module) ||
    (data.requires.premium && !get(data.state.isPremium))
  ) {
    logger.debug('module inactive or not premium');
    return;
  }
  const { awaitTask, isTaskRunning } = useTasks();

  const task = data.task;
  const { getStatus, setStatus } = getStatusUpdater(task.section);

  if (
    get(isTaskRunning(task.type, data.task.checkLoading)) ||
    (getStatus() === Status.LOADED && !data.refresh)
  ) {
    logger.debug(`${Section[data.task.section]} is already loading`);
    return;
  }

  setStatus(data.refresh ? Status.REFRESHING : Status.LOADING);

  try {
    const { taskId } = await task.query();
    const { result } = await awaitTask<R, T>(taskId, task.type, task.meta);
    set(state, task.parser ? task.parser(result) : result);
  } catch (e: any) {
    logger.error(`action failure for task ${TaskType[task.type]}:`, e);
    const { notify } = useNotifications();
    notify({
      title: task.onError.title,
      message: task.onError.error(e.message),
      severity: Severity.ERROR,
      display: true
    });
  }
  setStatus(Status.LOADED);
}

export function showError(description: string, title: string = '') {
  const { setMessage } = useMainStore();
  setMessage({
    title: title,
    description: description,
    success: false
  });
}

export function showMessage(description: string, title?: string): void {
  const { setMessage } = useMainStore();
  const message: Message = {
    title: title ?? i18n.t('message.success.title').toString(),
    description,
    success: true
  };
  setMessage(message);
}

export const getStatus = (section: Section) => {
  const { getStatus } = useMainStore();
  return get(getStatus(section));
};

export const setStatus: (newStatus: Status, section: Section) => void = (
  newStatus,
  section
) => {
  const { getStatus, setStatus } = useMainStore();
  if (get(getStatus(section)) === newStatus) {
    return;
  }
  setStatus({
    section: section,
    status: newStatus
  });
};

export const getStatusUpdater = (section: Section, ignore: boolean = false) => {
  const { setStatus, getStatus } = useMainStore();
  const updateStatus = (status: Status, otherSection?: Section) => {
    if (ignore) {
      return;
    }
    setStatus({
      section: otherSection ?? section,
      status: status
    });
  };

  const resetStatus = (otherSection?: Section) => {
    setStatus({
      section: otherSection ?? section,
      status: Status.NONE
    });
  };

  const loading = () => isLoading(get(getStatus(section)));
  const isFirstLoad = () => get(getStatus(section)) === Status.NONE;
  const getSectionStatus = (otherSection?: Section) => {
    return get(getStatus(otherSection ?? section));
  };
  return {
    loading,
    isFirstLoad,
    setStatus: updateStatus,
    getStatus: getSectionStatus,
    resetStatus
  };
};

export function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status === Status.REFRESHING
  );
}

export interface AddressEntries<T> {
  readonly [address: string]: T;
}

export function filterAddresses<T>(
  entries: AddressEntries<T>,
  addresses: string[],
  item: (item: T) => void
) {
  for (const address in entries) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    item(entries[address]);
  }
}
