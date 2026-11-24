import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

export type AlertType = 'success' | 'info' | 'warning' | 'error';

@Component({
  selector: 'app-alert',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!isDismissed()) {
      <div
        class="ant-alert"
        [class.ant-alert-success]="type() === 'success'"
        [class.ant-alert-info]="type() === 'info'"
        [class.ant-alert-warning]="type() === 'warning'"
        [class.ant-alert-error]="type() === 'error'"
        [class.ant-alert-with-description]="!!description()"
        role="alert"
      >
        @if (showIcon()) {
          <span class="ant-alert-icon">
            @if (type() === 'success') {
              <i class="fa-solid fa-circle-check"></i>
            } @else if (type() === 'error') {
              <i class="fa-solid fa-circle-xmark"></i>
            } @else if (type() === 'warning') {
              <i class="fa-solid fa-circle-exclamation"></i>
            } @else {
              <i class="fa-solid fa-circle-info"></i>
            }
          </span>
        }

        <div class="ant-alert-content">
          <div class="ant-alert-message">{{ message() }}</div>
          @if (description()) {
            <div class="ant-alert-description">{{ description() }}</div>
          }
        </div>

        @if (closable()) {
          <button
            type="button"
            class="ant-alert-close-icon"
            aria-label="Close alert"
            (click)="dismiss()"
          >
            <i class="fa-solid fa-xmark"></i>
          </button>
        }
      </div>
    }
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }

    .ant-alert {
      box-sizing: border-box;
      margin: 0;
      padding: 9px 14px;
      font-size: 13.5px;
      line-height: 1.5;
      border-radius: 8px;
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      word-break: break-word;
      transition: all 0.2s ease;
      font-family: inherit;

      &.ant-alert-with-description {
        padding: 14px 16px;
      }
    }

    /* Ant Design Alert Error */
    .ant-alert-error {
      background-color: #fff2f0;
      border: 1px solid #ffccc7;

      .ant-alert-icon {
        color: #ff4d4f;
      }

      .ant-alert-message {
        color: #cf1322;
      }

      .ant-alert-description {
        color: rgba(0, 0, 0, 0.75);
      }
    }

    /* Ant Design Alert Success */
    .ant-alert-success {
      background-color: #f6ffed;
      border: 1px solid #b7eb8f;

      .ant-alert-icon {
        color: #52c41a;
      }

      .ant-alert-message {
        color: #389e0d;
      }

      .ant-alert-description {
        color: rgba(0, 0, 0, 0.75);
      }
    }

    /* Ant Design Alert Warning */
    .ant-alert-warning {
      background-color: #fffbe6;
      border: 1px solid #ffe58f;

      .ant-alert-icon {
        color: #faad14;
      }

      .ant-alert-message {
        color: #d48806;
      }

      .ant-alert-description {
        color: rgba(0, 0, 0, 0.75);
      }
    }

    /* Ant Design Alert Info */
    .ant-alert-info {
      background-color: #e6f4ff;
      border: 1px solid #91caff;

      .ant-alert-icon {
        color: #1677ff;
      }

      .ant-alert-message {
        color: #0958d9;
      }

      .ant-alert-description {
        color: rgba(0, 0, 0, 0.75);
      }
    }

    .ant-alert-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      margin-top: 2px;
      flex-shrink: 0;
    }

    .ant-alert-content {
      flex: 1;
      min-width: 0;
    }

    .ant-alert-message {
      font-size: 13.5px;
      font-weight: 600;
      line-height: 1.45;
    }

    .ant-alert-description {
      font-size: 12.5px;
      margin-top: 3px;
      line-height: 1.4;
    }

    .ant-alert-close-icon {
      background: transparent;
      border: none;
      padding: 0;
      margin-left: 6px;
      cursor: pointer;
      color: rgba(0, 0, 0, 0.45);
      font-size: 13px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      border-radius: 4px;
      transition: all 0.15s ease;
      flex-shrink: 0;

      &:hover {
        color: rgba(0, 0, 0, 0.85);
        background-color: rgba(0, 0, 0, 0.06);
      }
    }
  `]
})
export class AlertComponent {
  readonly type = input<AlertType>('info');
  readonly message = input.required<string>();
  readonly description = input<string>();
  readonly showIcon = input<boolean>(true);
  readonly closable = input<boolean>(false);
  readonly closed = output<void>();

  readonly isDismissed = signal(false);

  dismiss(): void {
    this.isDismissed.set(true);
    this.closed.emit();
  }
}
