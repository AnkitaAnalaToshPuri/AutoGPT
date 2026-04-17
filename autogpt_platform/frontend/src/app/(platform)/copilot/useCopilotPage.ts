import { useSupabase } from "@/lib/supabase/hooks/useSupabase";
import { Flag, useGetFlag } from "@/services/feature-flags/use-get-flag";
import { concatWithAssistantMerge } from "./helpers/convertChatSessionToUiMessages";
import { useCopilotUIStore } from "./store";
import { useChatSession } from "./useChatSession";
import { useCopilotNotifications } from "./useCopilotNotifications";
import { useCopilotStream } from "./useCopilotStream";
import { useLoadMoreMessages } from "./useLoadMoreMessages";
import { useSendMessage } from "./useSendMessage";
import { useSessionTitlePoll } from "./useSessionTitlePoll";
import { useWorkflowImportAutoSubmit } from "./useWorkflowImportAutoSubmit";

export function useCopilotPage() {
  const { isUserLoading, isLoggedIn } = useSupabase();
  const isModeToggleEnabled = useGetFlag(Flag.CHAT_MODE_OPTION);

  const { copilotChatMode, copilotLlmModel, isDryRun } = useCopilotUIStore();

  const {
    sessionId,
    hydratedMessages,
    rawSessionMessages,
    historicalDurations,
    hasActiveStream,
    hasMoreMessages,
    oldestSequence,
    newestSequence,
    forwardPaginated,
    isLoadingSession,
    isSessionError,
    createSession,
    isCreatingSession,
    refetchSession,
    sessionDryRun,
  } = useChatSession({ dryRun: isDryRun });

  const {
    messages: currentMessages,
    sendMessage,
    stop,
    status,
    error,
    isReconnecting,
    isSyncing,
    isUserStoppingRef,
    rateLimitMessage,
    dismissRateLimit,
  } = useCopilotStream({
    sessionId,
    hydratedMessages,
    hasActiveStream,
    refetchSession,
    copilotMode: isModeToggleEnabled ? copilotChatMode : undefined,
    copilotModel: isModeToggleEnabled ? copilotLlmModel : undefined,
  });

  const { pagedMessages, hasMore, isLoadingMore, loadMore, resetPaged } =
    useLoadMoreMessages({
      sessionId,
      initialOldestSequence: oldestSequence,
      initialNewestSequence: newestSequence,
      initialHasMore: hasMoreMessages,
      forwardPaginated,
      initialPageRawMessages: rawSessionMessages,
    });

  // Combine paginated messages with current page messages, merging consecutive
  // assistant UIMessages at the page boundary so reasoning + response parts
  // stay in a single bubble.
  // Forward pagination (completed sessions): current page is the beginning,
  // paged messages are newer pages appended after.
  // Backward pagination (active sessions): paged messages are older history
  // prepended before the current page.
  const messages = forwardPaginated
    ? concatWithAssistantMerge(currentMessages, pagedMessages)
    : concatWithAssistantMerge(pagedMessages, currentMessages);

  useCopilotNotifications(sessionId);

  const { onSend, isUploadingFiles, pendingFilePartsRef } = useSendMessage({
    sessionId,
    sendMessage,
    createSession,
    forwardPaginated,
    pagedMessagesLength: pagedMessages.length,
    resetPaged,
    isUserStoppingRef,
  });

  useWorkflowImportAutoSubmit({ onSend, pendingFilePartsRef });

  useSessionTitlePoll({ sessionId, status, isReconnecting });

  return {
    sessionId,
    messages,
    status,
    error,
    stop,
    isReconnecting,
    isSyncing,
    isLoadingSession,
    isSessionError,
    isCreatingSession,
    isUploadingFiles,
    isUserLoading,
    isLoggedIn,
    createSession,
    onSend,
    hasMoreMessages: hasMore,
    isLoadingMore,
    loadMore,
    forwardPaginated,
    historicalDurations,
    rateLimitMessage,
    dismissRateLimit,
    // sessionDryRun is the CURRENT session's immutable dry_run flag from API,
    // used to render the banner. The global `isDryRun` preference (for new
    // sessions) lives in the store and is consumed by the toggle button.
    sessionDryRun,
  };
}
