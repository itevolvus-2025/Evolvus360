import { DatePipe } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-notification-dropdown',
  standalone: true,
  imports: [],
  template: `
    <div class="dropdown-wrap">
      <span class="icon-btn" aria-label="Notifications">
        <i class="fa-regular fa-bell"></i>
      </span>
    </div>
  `
})
export class NotificationDropdownComponent {}
