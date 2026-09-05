package accountprofile

import (
	"context"
	"testing"
	"time"

	"litepan/internal/driver"
)

type blockingProfileExecutor struct {
	started chan int64
	release chan struct{}
}

func (e *blockingProfileExecutor) Run(
	ctx context.Context,
	accountID int64,
	_ func(driver.Driver) error,
) error {
	select {
	case e.started <- accountID:
	case <-ctx.Done():
		return ctx.Err()
	}
	select {
	case <-e.release:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

func TestBackgroundProfileRefreshRunsSerially(t *testing.T) {
	exec := &blockingProfileExecutor{
		started: make(chan int64, 2),
		release: make(chan struct{}, 2),
	}
	svc := New(exec)
	done := make(chan struct{}, 2)
	start := make(chan struct{})

	for _, accountID := range []int64{1, 2} {
		go func(id int64) {
			<-start
			svc.refresh(context.Background(), id)
			done <- struct{}{}
		}(accountID)
	}
	close(start)

	select {
	case <-exec.started:
	case <-time.After(time.Second):
		t.Fatal("首个账号资料刷新未启动")
	}
	select {
	case id := <-exec.started:
		t.Fatalf("后台账号资料刷新发生并发，账号 %d 提前启动", id)
	case <-time.After(80 * time.Millisecond):
	}

	exec.release <- struct{}{}
	select {
	case <-exec.started:
	case <-time.After(time.Second):
		t.Fatal("首个刷新结束后，第二个账号资料刷新未启动")
	}
	exec.release <- struct{}{}

	for range 2 {
		select {
		case <-done:
		case <-time.After(time.Second):
			t.Fatal("后台账号资料刷新未结束")
		}
	}
}
