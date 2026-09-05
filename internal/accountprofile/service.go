package accountprofile

import (
	"context"
	"sync"
	"time"

	"litepan/internal/domain"
	"litepan/internal/driver"
)

type Executor interface {
	Run(context.Context, int64, func(driver.Driver) error) error
}

type Service struct {
	exec        Executor
	mu          sync.RWMutex
	profiles    map[int64]domain.AccountProfile
	refreshed   map[int64]string
	refreshGate chan struct{}
}

func New(exec Executor) *Service {
	return &Service{
		exec:        exec,
		profiles:    map[int64]domain.AccountProfile{},
		refreshed:   map[int64]string{},
		refreshGate: make(chan struct{}, 1),
	}
}

func (s *Service) Get(accountID int64) (domain.AccountProfile, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.profiles[accountID]
	return p, ok
}

func (s *Service) RefreshDaily(ctx context.Context, accounts []*domain.Account) {
	day := time.Now().Format("2006-01-02")
	for _, account := range accounts {
		if !account.IsActive {
			continue
		}
		prototype, ok := driver.New(account.DriverType)
		if !ok || !prototype.Config().SupportsAccountProfile {
			continue
		}
		s.mu.Lock()
		if s.refreshed[account.ID] == day {
			s.mu.Unlock()
			continue
		}
		s.refreshed[account.ID] = day
		s.mu.Unlock()
		go s.refresh(context.WithoutCancel(ctx), account.ID)
	}
}

func (s *Service) refresh(parent context.Context, accountID int64) {
	select {
	case s.refreshGate <- struct{}{}:
		defer func() { <-s.refreshGate }()
	case <-parent.Done():
		return
	}
	ctx, cancel := context.WithTimeout(parent, 45*time.Second)
	defer cancel()
	_, _ = s.Refresh(ctx, accountID)
}

// Refresh 立即更新单个账号资料，供用户手动刷新使用。
func (s *Service) Refresh(ctx context.Context, accountID int64) (*domain.AccountProfile, error) {
	var profile *domain.AccountProfile
	if err := s.exec.Run(ctx, accountID, func(d driver.Driver) error {
		p, ok := d.(driver.AccountProfileProvider)
		if !ok {
			return domain.Errf(domain.CodeNotImplement)
		}
		var err error
		profile, err = p.GetAccountProfile(ctx)
		return err
	}); err != nil {
		return nil, err
	}
	if profile == nil {
		return nil, domain.Errorf(domain.CodeDriverError, "未返回账号资料")
	}
	profile.AccountID = accountID
	profile.RefreshedAt = time.Now()
	s.mu.Lock()
	s.profiles[accountID] = *profile
	s.mu.Unlock()
	return profile, nil
}
