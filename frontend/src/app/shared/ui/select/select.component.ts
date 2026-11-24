import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  computed,
  forwardRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';
import { IconComponent } from '../icon/icon.component';

export interface SelectOption {
  label: string;
  value: any;
  disabled?: boolean;
}

@Component({
  selector: 'app-select',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SelectComponent),
      multi: true,
    },
  ],
  template: `
    <div
      class="ant-select-wrapper"
      [class.has-label]="!!label()"
    >
      @if (label()) {
        <label class="ant-select-label" [attr.for]="id()">
          {{ label() }}
          @if (required()) {
            <span class="required-star">*</span>
          }
        </label>
      }

      <div
        class="ant-select"
        [class.ant-select-open]="isOpen()"
        [class.ant-select-focused]="isOpen()"
        [class.ant-select-disabled]="disabled()"
        [class.ant-select-status-error]="status() === 'error'"
        [class.ant-select-status-warning]="status() === 'warning'"
        [class.ant-select-lg]="size() === 'large'"
        [class.ant-select-sm]="size() === 'small'"
        (click)="toggleOpen($event)"
        tabindex="0"
        (keydown)="onKeydown($event)"
        [attr.aria-expanded]="isOpen()"
        [attr.aria-disabled]="disabled()"
      >
        <div class="ant-select-selector">
          @if (showSearch() && isOpen()) {
            <input
              type="text"
              class="ant-select-selection-search-input"
              [value]="searchQuery()"
              (input)="onSearchInput($event)"
              (click)="$event.stopPropagation()"
              [placeholder]="selectedLabel() || placeholder()"
              autofocus
            />
          } @else if (selectedOption()) {
            <span class="ant-select-selection-item" [title]="selectedOption()!.label">
              {{ selectedOption()!.label }}
            </span>
          } @else {
            <span class="ant-select-selection-placeholder">
              {{ placeholder() }}
            </span>
          }

          @if (allowClear() && selectedOption() && !disabled()) {
            <span
              class="ant-select-clear"
              (click)="clearSelection($event)"
              title="Clear selection"
            >
              &times;
            </span>
          }

          <span class="ant-select-arrow" aria-hidden="true">
            <app-icon name="chevron-down" [size]="12" color="#8C8C8C" />
          </span>
        </div>

        @if (isOpen()) {
          <div
            class="ant-select-dropdown"
            (click)="$event.stopPropagation()"
            role="listbox"
          >
            @for (opt of filteredOptions(); track opt.value; let idx = $index) {
              <div
                class="ant-select-item ant-select-item-option"
                [class.ant-select-item-option-selected]="isSelected(opt.value)"
                [class.ant-select-item-option-disabled]="opt.disabled"
                (click)="onSelect(opt, $event)"
                role="option"
                [attr.aria-selected]="isSelected(opt.value)"
              >
                <span class="ant-select-item-option-content">{{ opt.label }}</span>
                @if (isSelected(opt.value)) {
                  <span class="ant-select-selected-icon">
                    <app-icon name="check" [size]="13" color="#1677FF" />
                  </span>
                }
              </div>
            } @empty {
              <div class="ant-select-item-empty">
                <span>No options available</span>
              </div>
            }
          </div>
        }
      </div>

      @if (errorMessage()) {
        <small class="ant-select-error-msg">{{ errorMessage() }}</small>
      }
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }

    .ant-select-wrapper {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 5px;
      width: 100%;

      .ant-select-label {
        font-size: 13px;
        font-weight: 600;
        color: #334155;
        margin: 0;

        .required-star {
          color: #ff4d4f;
          margin-left: 2px;
        }
      }

      .ant-select-error-msg {
        font-size: 12px;
        color: #ff4d4f;
        margin-top: 2px;
      }
    }

    .ant-select-item-empty {
      padding: 12px 14px;
      text-align: center;
      color: rgba(0, 0, 0, 0.45);
      font-size: 13px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SelectComponent implements ControlValueAccessor {
  private readonly elementRef = inject(ElementRef);

  // Inputs
  readonly options = input<SelectOption[]>([]);
  readonly placeholder = input<string>('Select an option');
  readonly label = input<string>('');
  readonly required = input<boolean>(false);
  readonly disabled = input<boolean>(false);
  readonly allowClear = input<boolean>(false);
  readonly showSearch = input<boolean>(false);
  readonly size = input<'small' | 'middle' | 'large'>('middle');
  readonly status = input<'error' | 'warning' | ''>('');
  readonly errorMessage = input<string>('');
  readonly id = input<string>('');

  // Outputs
  readonly valueChange = output<any>();

  // State signals
  readonly value = signal<any>(null);
  readonly isOpen = signal<boolean>(false);
  readonly searchQuery = signal<string>('');

  // ControlValueAccessor callbacks
  onChange: (value: any) => void = () => undefined;
  onTouched: () => void = () => undefined;

  // Computed properties
  readonly selectedOption = computed(() => {
    const currentVal = this.value();
    if (currentVal == null || currentVal === '') return null;
    return this.options().find((opt) => String(opt.value) === String(currentVal)) || null;
  });

  readonly selectedLabel = computed(() => {
    return this.selectedOption()?.label ?? '';
  });

  readonly filteredOptions = computed(() => {
    const list = this.options();
    const query = this.searchQuery().trim().toLowerCase();
    if (!query) return list;
    return list.filter((opt) => opt.label.toLowerCase().includes(query));
  });

  toggleOpen(event?: MouseEvent): void {
    if (this.disabled()) return;
    if (event) event.stopPropagation();
    this.isOpen.update((v) => !v);
    if (!this.isOpen()) {
      this.searchQuery.set('');
      this.onTouched();
    }
  }

  onSelect(opt: SelectOption, event: MouseEvent): void {
    event.stopPropagation();
    if (opt.disabled) return;
    this.value.set(opt.value);
    this.onChange(opt.value);
    this.valueChange.emit(opt.value);
    this.isOpen.set(false);
    this.searchQuery.set('');
    this.onTouched();
  }

  clearSelection(event: MouseEvent): void {
    event.stopPropagation();
    this.value.set(null);
    this.onChange(null);
    this.valueChange.emit(null);
    this.searchQuery.set('');
    this.onTouched();
  }

  onSearchInput(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.searchQuery.set(val);
  }

  isSelected(optVal: any): boolean {
    const current = this.value();
    return current != null && String(current) === String(optVal);
  }

  onKeydown(event: KeyboardEvent): void {
    if (this.disabled()) return;
    if (event.key === 'Escape') {
      this.isOpen.set(false);
      this.searchQuery.set('');
    } else if (event.key === 'Enter' || event.key === ' ') {
      if (!this.isOpen()) {
        event.preventDefault();
        this.toggleOpen();
      }
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      if (this.isOpen()) {
        this.isOpen.set(false);
        this.searchQuery.set('');
        this.onTouched();
      }
    }
  }

  // ControlValueAccessor methods
  writeValue(value: any): void {
    this.value.set(value);
  }

  registerOnChange(fn: (value: any) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState?(isDisabled: boolean): void {
    // Handled by signal
  }
}
