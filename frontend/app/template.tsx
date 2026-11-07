// A template (unlike a layout) re-mounts on every navigation, which replays this
// short fade so moving between Chat, Wall and AI feels continuous.
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col animate-in fade-in-0 slide-in-from-bottom-1 duration-300 motion-reduce:animate-none">
      {children}
    </div>
  );
}
