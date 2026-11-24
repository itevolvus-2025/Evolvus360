import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ant-message" aria-live="polite">
      @for (toast of notifications.toasts(); track toast.id) {
        <div
          class="ant-message-notice"
          [class.ant-message-success]="toast.type === 'success'"
          [class.ant-message-error]="toast.type === 'error'"
          [class.ant-message-info]="toast.type === 'info'"
          [class.ant-message-warning]="toast.type === 'warning'"
          role="status"
        >
          <div class="ant-message-notice-content">
            <span class="ant-message-custom-content">
              @if (toast.type === 'success') {
                <i class="fa-solid fa-circle-check ant-message-icon success-icon"></i>
              } @else if (toast.type === 'error') {
                <i class="fa-solid fa-circle-xmark ant-message-icon error-icon"></i>
              } @else if (toast.type === 'warning') {
                <i class="fa-solid fa-circle-exclamation ant-message-icon warning-icon"></i>
              } @else {
                <i class="fa-solid fa-circle-info ant-message-icon info-icon"></i>
              }
              <span class="ant-message-text">{{ toast.message }}</span>
            </span>
            <button
              type="button"
              class="ant-message-close"
              aria-label="Close notification"
              (click)="notifications.dismiss(toast.id)"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .ant-message {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      color: rgba(0, 0, 0, 0.88);
      font-size: 14px;
      line-height: 1.5;
      font-family: inherit;
      position: fixed;
      top: 24px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10000;
      width: auto;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }

    .ant-message-notice {
      text-align: center;
      pointer-events: auto;
      animation: antMessageSlideDown 0.28s cubic-bezier(0.23, 1, 0.32, 1);
    }

    .ant-message-notice-content {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 18px;
      background: #ffffff;
      border-radius: 8px;
      box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05);
      border: 1px solid rgba(0, 0, 0, 0.06);
    }

    .ant-message-custom-content {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      text-align: left;
    }

    .ant-message-icon {
      font-size: 16px;
      line-height: 1;
      flex-shrink: 0;

      &.success-icon {
        color: #52c41a;
      }
      &.error-icon {
        color: #ff4d4f;
      }
      &.warning-icon {
        color: #faad14;
      }
      &.info-icon {
        color: #1677ff;
      }
    }

    .ant-message-text {
      font-size: 13.5px;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.88);
      line-height: 1.4;
    }

    .ant-message-close {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin-left: 6px;
      background: transparent;
      border: none;
      color: rgba(0, 0, 0, 0.45);
      cursor: pointer;
      font-size: 12px;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.2s ease;
      line-height: 1;

      &:hover {
        color: rgba(0, 0, 0, 0.88);
        background: rgba(0, 0, 0, 0.06);
      }
    }

    @keyframes antMessageSlideDown {
      0% {
        opacity: 0;
        transform: translateY(-20px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `]
})
export class ToastContainerComponent {
  readonly notifications = inject(NotificationService);
}
