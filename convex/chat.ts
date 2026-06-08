import { action, internalAction, mutation, query } from "./_generated/server";
import { internal, components } from "./_generated/api";
import { listUIMessages, syncStreams, vStreamArgs } from "@convex-dev/agent";
import { paginationOptsValidator } from "convex/server";
import { v } from "convex/values";
import { investigatorAgent } from "./agent";

export const createThread = mutation({
  args: {},
  returns: v.object({ threadId: v.string() }),
  handler: async (ctx) => {
    const { threadId } = await investigatorAgent.createThread(ctx, {});
    return { threadId };
  },
});

export const sendMessage = mutation({
  args: { prompt: v.string(), threadId: v.string() },
  returns: v.string(),
  handler: async (ctx, { prompt, threadId }) => {
    const { messageId } = await investigatorAgent.saveMessage(ctx, {
      threadId,
      prompt,
      skipEmbeddings: true,
    });
    await ctx.scheduler.runAfter(0, internal.chat.generateResponse, {
      threadId,
      promptMessageId: messageId,
    });
    return messageId;
  },
});

export const generateResponse = internalAction({
  args: { promptMessageId: v.string(), threadId: v.string() },
  handler: async (ctx, { promptMessageId, threadId }) => {
    const result = await investigatorAgent.streamText(
      ctx,
      { threadId },
      { promptMessageId },
      { saveStreamDeltas: { throttleMs: 200, chunking: "word" } },
    );
    await result.consumeStream();
  },
});

export const listMessages = query({
  args: {
    threadId: v.string(),
    paginationOpts: paginationOptsValidator,
    streamArgs: vStreamArgs,
  },
  handler: async (ctx, args) => {
    const streams = await syncStreams(ctx, components.agent, args);
    const paginated = await listUIMessages(ctx, components.agent, args);
    return { ...paginated, streams };
  },
});

export const quickAnalyze = action({
  args: {
    prompt: v.string(),
  },
  returns: v.string(),
  handler: async (ctx, args) => {
    const { threadId } = await investigatorAgent.createThread(ctx, {});
    const { messageId } = await investigatorAgent.saveMessage(ctx, {
      threadId,
      prompt: args.prompt,
      skipEmbeddings: true,
    });
    const result = await investigatorAgent.streamText(
      ctx,
      { threadId },
      { messageId },
      { saveStreamDeltas: { throttleMs: 200, chunking: "word" } },
    );
    const response = await result.consumeStream();
    return response.text;
  },
});