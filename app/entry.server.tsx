/**
 * By default, Remix will handle generating the HTTP Response for you.
 * You are free to delete this file if you'd like to, but if you ever want it revealed again, you can run `npx remix reveal` ✨
 * For more information, see https://remix.run/file-conventions/entry.server
 */

import { PassThrough } from "node:stream";
import { CacheProvider as EmotionCacheProvider } from "@emotion/react";
import createEmotionCache from "@emotion/cache";
// TODO: See TODO messages below
// import createEmotionServer from "@emotion/server/create-instance";
import type { AppLoadContext, EntryContext } from "@remix-run/node";
import { createReadableStreamFromReadable } from "@remix-run/node";
import { RemixServer } from "@remix-run/react";
import { isbot } from "isbot";
import { renderToPipeableStream } from "react-dom/server";

const ABORT_DELAY = 5_000;

export default function handleRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  remixContext: EntryContext,
  // This is ignored so we can keep it in the template for visibility.  Feel
  // free to delete this parameter in your app if you're not using it!
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  loadContext: AppLoadContext
) {
  return isbot(request.headers.get("user-agent") || "")
    ? handleBotRequest(
        request,
        responseStatusCode,
        responseHeaders,
        remixContext
      )
    : handleBrowserRequest(
        request,
        responseStatusCode,
        responseHeaders,
        remixContext
      );
}

function handleBotRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  remixContext: EntryContext
) {
  return new Promise((resolve, reject) => {
    let shellRendered = false;
    const emotionCache = createEmotionCache({ key: "css" });

    const { pipe, abort } = renderToPipeableStream(
      <EmotionCacheProvider value={emotionCache}>
        <RemixServer
          context={remixContext}
          url={request.url}
          abortDelay={ABORT_DELAY}
        />
      </EmotionCacheProvider>,
      {
        onAllReady() {
          shellRendered = true;
          const body = new PassThrough();

          // TODO: The example in the remix-run repo for adding Chakra UI is
          // out of date, and the 'bodyWithStyles' steam is incompatible
          // with the stream created by 'createReadableStreamFromReadable'.
          // Figuring out how to get them to play nice would require digging
          // into package source code and researching the intricacies of
          // JS streams, and I don't care enough to bother.
          // Leaving the code from the example here in case I decide to
          // dedicate the time to figure it out later.
          // const emotionServer = createEmotionServer(emotionCache);
          // const bodyWithStyles = emotionServer.renderStylesToNodeStream();
          // body.pipe(bodyWithStyles)
          const stream = createReadableStreamFromReadable(body);

          responseHeaders.set("Content-Type", "text/html");

          resolve(
            new Response(stream, {
              headers: responseHeaders,
              status: responseStatusCode,
            })
          );

          pipe(body);
        },
        onShellError(error: unknown) {
          reject(error);
        },
        onError(error: unknown) {
          responseStatusCode = 500;
          // Log streaming rendering errors from inside the shell.  Don't log
          // errors encountered during initial shell rendering since they'll
          // reject and get logged in handleDocumentRequest.
          if (shellRendered) {
            console.error(error);
          }
        },
      }
    );

    setTimeout(abort, ABORT_DELAY);
  });
}

function handleBrowserRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  remixContext: EntryContext
) {
  return new Promise((resolve, reject) => {
    let shellRendered = false;
    const emotionCache = createEmotionCache({ key: "css" });

    const { pipe, abort } = renderToPipeableStream(
      <EmotionCacheProvider value={emotionCache}>
        <RemixServer
          context={remixContext}
          url={request.url}
          abortDelay={ABORT_DELAY}
        />
      </EmotionCacheProvider>,
      {
        onShellReady() {
          shellRendered = true;
          const body = new PassThrough();

          // TODO: The example in the remix-run repo for adding Chakra UI is
          // out of date, and the 'bodyWithStyles' steam is incompatible
          // with the stream created by 'createReadableStreamFromReadable'.
          // Figuring out how to get them to play nice would require digging
          // into package source code and researching the intricacies of
          // JS streams, and I don't care enough to bother.
          // Leaving the code from the example here in case I decide to
          // dedicate the time to figure it out later.
          // const emotionServer = createEmotionServer(emotionCache);
          // const bodyWithStyles = emotionServer.renderStylesToNodeStream();
          // body.pipe(bodyWithStyles);
          const stream = createReadableStreamFromReadable(body);

          responseHeaders.set("Content-Type", "text/html");

          resolve(
            new Response(stream, {
              headers: responseHeaders,
              status: responseStatusCode,
            })
          );

          pipe(body);
        },
        onShellError(error: unknown) {
          reject(error);
        },
        onError(error: unknown) {
          responseStatusCode = 500;
          // Log streaming rendering errors from inside the shell.  Don't log
          // errors encountered during initial shell rendering since they'll
          // reject and get logged in handleDocumentRequest.
          if (shellRendered) {
            console.error(error);
          }
        },
      }
    );

    setTimeout(abort, ABORT_DELAY);
  });
}
