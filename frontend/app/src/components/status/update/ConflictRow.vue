<template>
  <v-row class="mt-2 mb-2" no-gutters>
    <v-col cols="auto" class="font-weight-medium"> {{ field }}: </v-col>
    <v-col class="ms-4" :class="diff ? 'red--text' : null">
      <span v-if="isStarted">
        <date-display :timestamp="value" no-timezone />
      </span>
      <span v-else-if="isAddress">
        <hash-link :text="value" no-link />
      </span>
      <span v-else>
        {{ value }}
      </span>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ConflictRow extends Vue {
  @Prop({ required: true, type: String })
  field!: string;
  @Prop({ required: true })
  value!: string;
  @Prop({ required: true, type: Boolean })
  diff!: boolean;

  get isStarted(): boolean {
    return this.field === 'started';
  }

  get isAddress(): boolean {
    return this.field === 'ethereumAddress';
  }
}
</script>

<style scoped lang="scss"></style>
