/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Listens for the custom `activity_dm/open_chat` bus notification sent
 * from the server when an activity is assigned to the current user, and
 * force-opens the corresponding Discuss chat window in the bottom-right
 * corner — even if the user had previously closed it.
 */
const activityDmOpenChatService = {
    dependencies: ["bus_service", "mail.store", "mail.chat_window"],

    start(env, services) {
        const bus = services.bus_service;
        const store = services["mail.store"];
        const chatWindow = services["mail.chat_window"];

        bus.subscribe("activity_dm/open_chat", async ({ channel_id }) => {
            if (!channel_id) {
                return;
            }
            // Get-or-insert the thread record. If the message_post bus
            // event arrived just before this one, the thread is already
            // populated; otherwise we create a stub that the chat window
            // will hydrate when it opens.
            let thread;
            try {
                thread = store.Thread.insert({
                    id: channel_id,
                    model: "discuss.channel",
                });
            } catch (e) {
                console.warn("activity_dm: could not resolve thread", e);
                return;
            }
            if (!thread) {
                return;
            }
            try {
                await chatWindow.open(thread, { focus: true });
            } catch (e) {
                console.warn("activity_dm: could not open chat window", e);
            }
        });
    },
};

registry
    .category("services")
    .add("activity_dm_notification.open_chat", activityDmOpenChatService);
