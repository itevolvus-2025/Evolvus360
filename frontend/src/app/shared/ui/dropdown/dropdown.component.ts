import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  computed,
  forwardRef,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';
import { IconComponent } from '../icon/icon.component';

export interface DropdownOption {
  label: string;
  value: any;
  icon?: string;
  disabled?: boolean;
}

@Component({
  selector: 'app-dropdown',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => DropdownComponent),
      multi: true,
    },
  ],
  template: `
    <div
      class="app-dropdown-container"
      [class.has-label]="!!label"
      [class.is-open]="isOpen()"
      [class.is-disabled]="isDisabled()"
      [class.size-sm]="size === 'sm'"
      [class.size-lg]="size === 'lg'"
      [style.width]="width"
    >
      @if (label) {
        <label class="dropdown-label" [attr.for]="id">
          {{ label }}
          @if (required) {
            <span class="required-star">*</span>
          }
        </label>
      }

      <div class="dropdown-box">
        <!-- Dropdown Trigger Button -->
        <button
          type="button"
          class="dropdown-trigger-btn"
          [class.variant-filter]="variant === 'filter'"
          [class.has-error]="status === 'error' || !!errorMessage"
          [class.has-warning]="status === 'warning'"
          [class.is-open]="isOpen()"
          [class.is-active-filter]="variant === 'filter' && selectedOption() && selectedOption()!.value !== 'All'"
          [attr.id]="id"
          [attr.aria-expanded]="isOpen()"
          [disabled]="isDisabled()"
          (click)="toggleOpen($event)"
        >
          <div class="trigger-content-left">
            @if (icon) {
              <app-icon
                [name]="icon"
                [size]="size === 'sm' ? 12 : 14"
                [color]="isOpen() || (selectedOption() && selectedOption()!.value !== 'All') ? '#2563EB' : '#64748B'"
                class="trigger-icon"
              />
            }
            @if (selectedOption()) {
              <span class="selected-label-text">{{ selectedOption()!.label }}</span>
            } @else {
              <span class="placeholder-text">{{ placeholder }}</span>
            }
          </div>

          <div class="trigger-content-right">
            @if (allowClear && selectedOption() && !isDisabled()) {
              <span
                class="clear-selection-btn"
                (click)="clearSelection($event)"
                title="Clear selection"
                aria-label="Clear selection"
              >
                &times;
              </span>
            }
            <span class="dropdown-chevron-arrow" [class.rotated]="isOpen()">
              <app-icon name="chevron-down" [size]="size === 'sm' ? 10 : 12" [color]="isOpen() ? '#2563EB' : '#64748B'" />
            </span>
          </div>
        </button>

        <!-- Dropdown Popover Overlay -->
        @if (isOpen()) {
          <div
            class="dropdown-popover-menu"
            (click)="$event.stopPropagation()"
            role="listbox"
          >
            @if (showSearch) {
              <div class="dropdown-search-wrapper">
                <app-icon name="search" [size]="13" color="#94A3B8" />
                <input
                  type="text"
                  class="dropdown-search-input"
                  [value]="searchQuery()"
                  (input)="onSearchInput($event)"
                  placeholder="Search..."
                  (click)="$event.stopPropagation()"
                  autofocus
                />
              </div>
            }

            <div class="dropdown-options-list">
              @for (opt of filteredOptions(); track opt.value) {
                <button
                  type="button"
                  class="dropdown-option-item"
                  [class.is-selected]="isSelected(opt.value)"
                  [class.is-disabled]="opt.disabled"
                  [disabled]="opt.disabled"
                  (click)="onSelectOption(opt, $event)"
                  role="option"
                  [attr.aria-selected]="isSelected(opt.value)"
                >
                  <div class="option-label-wrapper">
                    @if (opt.icon) {
                      <app-icon
                        [name]="opt.icon"
                        [size]="14"
                        [color]="isSelected(opt.value) ? '#2563EB' : '#64748B'"
                      />
                    }
                    <span class="option-label">{{ opt.label }}</span>
                  </div>

                  @if (isSelected(opt.value)) {
                    <app-icon name="check" [size]="13" color="#2563EB" class="option-check-icon" />
                  }
                </button>
              } @empty {
                <div class="dropdown-empty-state">
                  <span>No options found</span>
                </div>
              }
            </div>
          </div>
        }
      </div>

      @if (errorMessage) {
        <small class="dropdown-error-text">{{ errorMessage }}</small>
      }
    </div>
  `,
  styles: [`
    :host {
      display: inline-block;
      width: 100%;
      vertical-align: middle;
      font-family: inherit;
    }

    .app-dropdown-container {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 5px;
      width: 100%;

      &.size-sm {
        .dropdown-trigger-btn {
          min-height: 32px;
          padding: 4px 10px;
          font-size: 12.5px;
          border-radius: 6px;
        }
      }

      &.size-lg {
        .dropdown-trigger-btn {
          min-height: 44px;
          padding: 8px 16px;
          font-size: 14.5px;
          border-radius: 8px;
        }
      }
    }

    .dropdown-label {
      font-size: 13px;
      font-weight: 600;
      color: #334155;
      margin: 0;

      .required-star {
        color: #ef4444;
        margin-left: 2px;
      }
    }

    .dropdown-box {
      position: relative;
      width: 100%;
    }

    /* ==========================================================================
       Trigger Button (Blue Theme Rounded Corners)
       ========================================================================== */
    .dropdown-trigger-btn {
      width: 100%;
      min-height: 40px;
      box-sizing: border-box;
      background-color: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 7px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      cursor: pointer;
      font-family: inherit;
      color: #0f172a;
      outline: none;
      transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
      text-align: left;

      &:hover:not(:disabled) {
        border-color: #93c5fd;
        background-color: #f8fafc;
      }

      &:focus-visible,
      &.is-open {
        border-color: #2563eb;
        background-color: #ffffff;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
      }

      &.has-error {
        border-color: #ef4444 !important;
        &:focus-visible,
        &.is-open {
          box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.14) !important;
        }
      }

      &:disabled {
        background-color: #f1f5f9;
        border-color: #e2e8f0;
        color: #94a3b8;
        cursor: not-allowed;
      }

      &.variant-filter {
        min-height: 38px;
        font-weight: 500;
        font-size: 13px;

        &.is-active-filter {
          border-color: #2563eb;
          color: #2563eb;
          background-color: #eff6ff;
        }
      }

      .trigger-content-left {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        flex: 1;
        overflow: hidden;

        .trigger-icon {
          flex-shrink: 0;
          display: flex;
          align-items: center;
        }

        .selected-label-text {
          font-size: 13.5px;
          font-weight: 500;
          color: #0f172a;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .placeholder-text {
          font-size: 13.5px;
          color: #94a3b8;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .trigger-content-right {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;

        .clear-selection-btn {
          font-size: 16px;
          line-height: 1;
          color: #94a3b8;
          cursor: pointer;
          padding: 0 2px;
          transition: color 0.15s ease;

          &:hover {
            color: #ef4444;
          }
        }

        .dropdown-chevron-arrow {
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);

          &.rotated {
            transform: rotate(180deg);
          }
        }
      }
    }

    /* ==========================================================================
       Popover Menu (Blue Theme Rounded Corners)
       ========================================================================== */
    .dropdown-popover-menu {
      position: absolute;
      top: calc(100% + 5px);
      left: 0;
      min-width: 100%;
      width: max-content;
      max-width: 360px;
      z-index: 1050;
      background-color: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 5px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
      animation: dropdownFadeIn 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    }

    @keyframes dropdownFadeIn {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .dropdown-search-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      margin-bottom: 4px;
      background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;

      .dropdown-search-input {
        border: none;
        outline: none;
        background: transparent;
        font-family: inherit;
        font-size: 13px;
        color: #0f172a;
        width: 100%;

        &::placeholder {
          color: #94a3b8;
        }
      }
    }

    .dropdown-options-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
      max-height: 250px;
      overflow-y: auto;
      scrollbar-width: thin;
    }

    .dropdown-option-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      width: 100%;
      padding: 8px 12px;
      background: transparent;
      border: none;
      border-radius: 6px;
      font-family: inherit;
      font-size: 13px;
      font-weight: 500;
      color: #334155;
      text-align: left;
      cursor: pointer;
      outline: none;
      transition: background-color 0.12s ease, color 0.12s ease;

      &:hover:not(:disabled) {
        background-color: #f1f5f9;
        color: #0f172a;
      }

      &.is-selected {
        background-color: #eff6ff;
        color: #2563eb;
        font-weight: 600;
      }

      &.is-disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .option-label-wrapper {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;

        .option-label {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .option-check-icon {
        flex-shrink: 0;
      }
    }

    .dropdown-empty-state {
      padding: 12px;
      text-align: center;
      font-size: 13px;
      color: #94a3b8;
    }

    .dropdown-error-text {
      font-size: 12px;
      color: #ef4444;
      margin-top: 1px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DropdownComponent implements ControlValueAccessor {
  private readonly elementRef = inject(ElementRef);

  // Configuration Inputs
  @Input() set options(opts: Array<DropdownOption | string>) {
    const normalized: DropdownOption[] = (opts || []).map((item) => {
      if (typeof item === 'string') {
        return { label: item, value: item };
      }
      return item;
    });
    this.normalizedOptions.set(normalized);
  }

  @Input() placeholder = 'Select option';
  @Input() label = '';
  @Input() required = false;
  private _disabled = false;
  @Input() set disabled(val: boolean) {
    this._disabled = val;
    this.isDisabled.set(val);
  }
  get disabled(): boolean {
    return this._disabled;
  }
  @Input() allowClear = false;
  @Input() showSearch = false;
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() variant: 'default' | 'filter' = 'default';
  @Input() icon = '';
  @Input() status: 'error' | 'warning' | '' = '';
  @Input() errorMessage = '';
  @Input() id = '';
  @Input() width = '100%';
  @Input() resetOnSelect = false;

  // Two-way value binding support
  @Input() set value(val: any) {
    this.selectedValue.set(val);
  }
  @Output() valueChange = new EventEmitter<any>();
  @Output() select = new EventEmitter<DropdownOption>();

  // Reactive state signals
  readonly normalizedOptions = signal<DropdownOption[]>([]);
  readonly selectedValue = signal<any>(null);
  readonly isOpen = signal<boolean>(false);
  readonly searchQuery = signal<string>('');
  readonly isDisabled = signal<boolean>(false);

  // ControlValueAccessor Callbacks
  onChange: (val: any) => void = () => undefined;
  onTouched: () => void = () => undefined;

  // Selected Option Object
  readonly selectedOption = computed<DropdownOption | null>(() => {
    const val = this.selectedValue();
    if (val === null || val === undefined || val === '') return null;
    return this.normalizedOptions().find((opt) => String(opt.value) === String(val)) || null;
  });

  // Filtered Options for Search
  readonly filteredOptions = computed<DropdownOption[]>(() => {
    const list = this.normalizedOptions();
    const q = this.searchQuery().trim().toLowerCase();
    if (!q) return list;
    return list.filter((opt) => opt.label.toLowerCase().includes(q));
  });

  toggleOpen(event: MouseEvent): void {
    if (this.isDisabled()) return;
    event.stopPropagation();
    this.isOpen.update((open) => !open);
    if (!this.isOpen()) {
      this.searchQuery.set('');
    }
  }

  onSelectOption(option: DropdownOption, event: MouseEvent): void {
    event.stopPropagation();
    if (option.disabled) return;

    if (this.resetOnSelect) {
      this.selectedValue.set(null);
      this.onChange(null);
    } else {
      this.selectedValue.set(option.value);
      this.onChange(option.value);
    }
    this.onTouched();
    this.valueChange.emit(option.value);
    this.select.emit(option);
    this.isOpen.set(false);
    this.searchQuery.set('');
  }

  clearSelection(event: MouseEvent): void {
    event.stopPropagation();
    if (this.isDisabled()) return;

    this.selectedValue.set(null);
    this.onChange(null);
    this.onTouched();
    this.valueChange.emit(null);
  }

  onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.searchQuery.set(target.value);
  }

  isSelected(optVal: any): boolean {
    const current = this.selectedValue();
    if (current === null || current === undefined) return false;
    return String(current) === String(optVal);
  }

  // Dismiss dropdown on outside clicks
  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
      this.searchQuery.set('');
    }
  }

  @HostListener('keydown.escape')
  onEscape(): void {
    this.isOpen.set(false);
    this.searchQuery.set('');
  }

  // ControlValueAccessor Implementation
  writeValue(value: any): void {
    this.selectedValue.set(value);
  }

  registerOnChange(fn: (val: any) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(disabled: boolean): void {
    this.isDisabled.set(disabled || this.disabled);
  }
}
