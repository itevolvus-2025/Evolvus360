import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal
} from '@angular/core';
import { APP_ICONS } from '../../shared/ui/icon/icons';
import { IconComponent } from '../../shared/ui/icon/icon.component';

interface ColorPreset {
  name: string;
  hex: string;
}

@Component({
  selector: 'app-icons-gallery',
  standalone: true,
  imports: [IconComponent],
  templateUrl: './icons-gallery.component.html',
  styleUrl: './icons-gallery.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IconsGalleryComponent {
  /** All icon keys extracted from APP_ICONS store */
  readonly allIcons = Object.keys(APP_ICONS).map((name) => ({ name }));

  /** Search query signal */
  readonly searchQuery = signal('');

  /** Selected size in pixels */
  readonly selectedSize = signal(20);

  /** Selected color in hex */
  readonly selectedColor = signal('#2563EB');

  /** Last copied icon key for UI feedback */
  readonly copiedIcon = signal<string | null>(null);

  readonly colorPresets: ColorPreset[] = [
    { name: 'Primary Blue', hex: '#2563EB' },
    { name: 'Emerald Green', hex: '#10B981' },
    { name: 'Amber Warning', hex: '#F59E0B' },
    { name: 'Rose Red', hex: '#EF4444' },
    { name: 'Indigo Purple', hex: '#6366F1' },
    { name: 'Slate Gray', hex: '#64748B' },
    { name: 'Dark Slate', hex: '#0F172A' }
  ];

  readonly iconCount = computed(() => this.allIcons.length);

  /** Filter icons by search query */
  readonly filteredIcons = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    if (!q) {
      return this.allIcons;
    }
    return this.allIcons.filter((i) => i.name.toLowerCase().includes(q));
  });

  onSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchQuery.set(value);
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  onSizeChange(event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    this.selectedSize.set(val);
  }

  onColorChange(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.selectedColor.set(val);
  }

  copyIconCode(iconName: string): void {
    const size = this.selectedSize();
    const color = this.selectedColor();

    let snippet = `<app-icon name="${iconName}" [size]="${size}"`;
    if (color !== 'currentColor') {
      snippet += ` color="${color}"`;
    }
    snippet += ` />`;

    navigator.clipboard?.writeText(snippet);
    this.copiedIcon.set(iconName);

    setTimeout(() => {
      if (this.copiedIcon() === iconName) {
        this.copiedIcon.set(null);
      }
    }, 2000);
  }
}

