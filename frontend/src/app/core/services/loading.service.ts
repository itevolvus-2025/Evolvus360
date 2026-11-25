import { Injectable, computed, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  /** Count of active in-flight HTTP requests or manual loading tasks */
  private readonly activeRequests = signal<number>(0);

  /** Dynamic message to display in the loader */
  private readonly currentMessage = signal<string>('Loading, please wait...');

  /** Readonly signal indicating if any loading operation is currently ongoing */
  readonly isLoading = computed(() => this.activeRequests() > 0);

  /** Readonly signal for the current loading message */
  readonly message = computed(() => this.currentMessage());

  /**
   * Start a loading operation. Increments active request count.
   * @param message Optional custom message for this operation
   */
  show(message?: string): void {
    if (message) {
      this.currentMessage.set(message);
    }
    this.activeRequests.update((count) => count + 1);
  }

  /**
   * End a loading operation. Decrements active request count.
   */
  hide(): void {
    this.activeRequests.update((count) => {
      const next = count > 0 ? count - 1 : 0;
      if (next === 0) {
        this.currentMessage.set('Loading, please wait...');
      }
      return next;
    });
  }

  /**
   * Force reset all active loading operations
   */
  reset(): void {
    this.activeRequests.set(0);
    this.currentMessage.set('Loading, please wait...');
  }
}
