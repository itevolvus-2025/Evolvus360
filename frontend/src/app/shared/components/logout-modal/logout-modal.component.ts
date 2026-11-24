import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { IconComponent } from '../../ui/icon/icon.component';

@Component({
  selector: 'app-logout-modal',
  standalone: true,
  imports: [CommonModule, IconComponent],
  template: `
    @if (isOpen()) {
      <div
        class="logout-modal-backdrop"
        (click)="onBackdropClick($event)"
        aria-hidden="true"
      >
        <div
          class="logout-modal-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-dialog-title"
          (click)="$event.stopPropagation()"
        >
          <!-- Header: Red Icon badge + Title + Close button -->
          <div class="logout-modal-header">
            <div class="logout-header-left">
              <div class="logout-icon-badge" aria-hidden="true">
                <app-icon name="logout" [size]="20" color="#EF4444" />
              </div>
              <h2 id="logout-dialog-title" class="logout-title">{{ title() }}</h2>
            </div>

            <button
              type="button"
              class="logout-close-btn"
              (click)="closeModal.emit()"
              title="Close"
              aria-label="Close dialog"
            >
              <app-icon name="close" [size]="18" color="#64748B" />
            </button>
          </div>

          <!-- Body: Confirmation message -->
          <div class="logout-modal-body">
            <p class="logout-message">{{ message() }}</p>
          </div>

          <!-- Divider -->
          <div class="logout-divider" aria-hidden="true"></div>

          <!-- Footer Actions: Cancel + Logout buttons -->
          <div class="logout-modal-footer">
            <button
              type="button"
              class="btn-logout-cancel"
              (click)="closeModal.emit()"
            >
              {{ cancelLabel() }}
            </button>
            <button
              type="button"
              class="btn-logout-confirm"
              (click)="confirmLogout.emit()"
            >
              {{ confirmLabel() }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    :host {
      display: contents;
    }

    .logout-modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 10000;
      background-color: rgba(15, 23, 42, 0.45);
      backdrop-filter: blur(2.5px);
      -webkit-backdrop-filter: blur(2.5px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
      animation: backdropFadeIn 0.18s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .logout-modal-dialog {
      background-color: #ffffff;
      border-radius: 20px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.06);
      width: 100%;
      max-width: 480px;
      padding: 24px 28px 20px 28px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      animation: modalPopIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .logout-modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .logout-header-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .logout-icon-badge {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background-color: #fef2f2;
      border: 1px solid #fee2e2;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .logout-title {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: -0.01em;
      line-height: 1.2;
    }

    .logout-close-btn {
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 6px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #64748b;
      transition: all 0.15s ease;
      outline: none;

      &:hover {
        background-color: #f1f5f9;
        color: #0f172a;
      }

      &:focus-visible {
        box-shadow: 0 0 0 2px #2563eb;
      }
    }

    .logout-modal-body {
      margin-top: 16px;
      margin-bottom: 20px;
    }

    .logout-message {
      margin: 0;
      font-size: 14px;
      line-height: 1.55;
      color: #64748b;
      font-weight: 400;
    }

    .logout-divider {
      width: 100%;
      height: 1px;
      background-color: #f1f5f9;
      margin-bottom: 18px;
    }

    .logout-modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
    }

    .btn-logout-cancel {
      background-color: #ffffff;
      border: 1.5px solid #60a5fa;
      color: #2563eb;
      font-size: 14px;
      font-weight: 600;
      padding: 7px 24px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
      outline: none;
      font-family: inherit;

      &:hover {
        background-color: #eff6ff;
        border-color: #2563eb;
      }

      &:focus-visible {
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25);
      }
    }

    .btn-logout-confirm {
      background-color: #ffffff;
      border: 1.5px solid #f87171;
      color: #ef4444;
      font-size: 14px;
      font-weight: 600;
      padding: 7px 24px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
      outline: none;
      font-family: inherit;

      &:hover {
        background-color: #fef2f2;
        border-color: #ef4444;
        color: #dc2626;
      }

      &:focus-visible {
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.25);
      }
    }

    @keyframes backdropFadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    @keyframes modalPopIn {
      from {
        opacity: 0;
        transform: scale(0.95) translateY(-6px);
      }
      to {
        opacity: 1;
        transform: scale(1) translateY(0);
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LogoutModalComponent {
  readonly isOpen = input<boolean>(false);
  readonly title = input<string>('Logout?');
  readonly message = input<string>(
    "You'll be signed out of your account. Are you sure you want to continue?"
  );
  readonly cancelLabel = input<string>('Cancel');
  readonly confirmLabel = input<string>('Logout');

  readonly closeModal = output<void>();
  readonly confirmLogout = output<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen()) {
      this.closeModal.emit();
    }
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeModal.emit();
    }
  }
}
