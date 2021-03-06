<template>
  <v-navigation-drawer
    class="notification-sidebar"
    :class="
      $vuetify.breakpoint.smAndDown ? 'notification-sidebar--mobile' : null
    "
    width="400px"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="input($event)"
  >
    <v-row align="center" no-gutters class="pl-2 pr-2 pt-1 pb-2">
      <v-col cols="auto">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              class="notification-sidebar__close"
              text
              icon
              v-on="on"
              @click="close()"
            >
              <v-icon>mdi-chevron-right</v-icon>
            </v-btn>
          </template>
          <span v-text="$t('notification_sidebar.close_tooltip')" />
        </v-tooltip>
      </v-col>
      <v-col>
        <span
          class="text-uppercase text--secondary text-caption font-weight-medium pl-1"
          v-text="$t('notification_sidebar.title')"
        />
      </v-col>
      <v-col cols="auto">
        <v-btn
          text
          class="text-caption text-lowercase"
          color="accent"
          :disabled="notifications.length === 0"
          @click="confirmClear = true"
          v-text="$t('notification_sidebar.clear_tooltip')"
        />
      </v-col>
    </v-row>
    <v-row no-gutters class="notification-sidebar__details">
      <v-col
        v-if="notifications.length === 0"
        class="notification-sidebar__no-messages"
      >
        <v-icon size="64px" color="primary">mdi-information</v-icon>
        <p
          class="notification-sidebar__no-messages__label"
          v-text="$t('notification_sidebar.no_messages')"
        />
      </v-col>
      <v-col v-else class="notification-sidebar__messages pl-2">
        <notification
          v-for="notification in notifications"
          :key="notification.id"
          class="mb-2"
          :notification="notification"
          @dismiss="remove($event)"
        />
      </v-col>
    </v-row>
    <confirm-dialog
      :display="confirmClear"
      :title="$t('notification_sidebar.confirmation.title')"
      :message="$t('notification_sidebar.confirmation.message')"
      @cancel="confirmClear = false"
      @confirm="clear()"
    />
  </v-navigation-drawer>
</template>

<script lang="ts">
import orderBy from 'lodash/orderBy';
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapMutations, mapState } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Notification from '@/components/status/notifications/Notification.vue';
import { NotificationData } from '@/store/notifications/types';

@Component({
  components: { Notification, ConfirmDialog },
  computed: {
    ...mapState('notifications', ['data'])
  },
  methods: {
    ...mapMutations('notifications', ['remove', 'reset'])
  }
})
export default class NotificationSidebar extends Vue {
  @Prop({ required: true, type: Boolean })
  visible!: boolean;

  data!: NotificationData[];
  confirmClear: boolean = false;
  copyText: string = '';
  remove!: (id: number) => void;
  reset!: () => void;

  clear() {
    this.confirmClear = false;
    this.reset();
    this.close();
  }

  input(visible: boolean) {
    if (visible) {
      return;
    }
    this.close();
  }

  @Emit()
  close() {}

  get notifications(): NotificationData[] {
    return orderBy(this.data, 'id', 'desc');
  }
}
</script>

<style scoped lang="scss">
.notification-sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  &.v-navigation-drawer {
    &--is-mobile {
      padding-top: 0 !important;
    }
  }

  &--mobile {
    top: 56px !important;
  }

  &__details {
    background-color: white;
    overflow-y: hidden;
    height: calc(100% - 64px);
    font-weight: 400;
    color: rgba(0, 0, 0, 0.87);
  }

  &__no-messages {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    &__label {
      font-size: 22px;
      margin-top: 22px;
      font-weight: 300;
      color: rgb(0, 0, 0, 0.6);
    }
  }

  &__messages {
    height: calc(100% - 64px);
    overflow-y: scroll !important;
  }

  @media only screen and (max-width: 960px) {
    top: 56px !important;
  }
}

::v-deep {
  .v-badge {
    &__badge {
      top: 0 !important;
      right: 0 !important;
    }
  }

  .v-list-item {
    &__action-text {
      margin-right: -8px;
      margin-top: -8px;
    }
  }
}
</style>
